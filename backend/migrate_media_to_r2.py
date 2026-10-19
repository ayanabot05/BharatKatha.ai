"""Upload existing local media into Cloudflare R2.

One-off migration for moving media off local disk. Safe to re-run: an object
already present in R2 is skipped, so an interrupted run just continues.

    python migrate_media_to_r2.py                 # dry run, reports only
    python migrate_media_to_r2.py --apply         # upload everything missing
    python migrate_media_to_r2.py --apply --limit 25

The `files` table is the source of truth for which objects exist; the local
media directory is the byte source. Local files are never deleted, so the old
copy remains as a rollback while R2 proves itself.

Related flags:
    --include-deleted   also migrate objects whose row is soft-deleted
    --verify            after upload, download each object back and compare
"""
from __future__ import annotations

import argparse
import asyncio
import mimetypes
import os
import sys
from pathlib import Path

import r2_storage
from core import CACHE, STORAGE_ROOT, db


def _safe_local_path(path: str) -> Path | None:
    """Resolve a storage path to a file under the media root, or None."""
    if not path or "\\" in path or path.startswith("/") or ".." in path.split("/"):
        return None
    try:
        target = (STORAGE_ROOT / path).resolve()
        if not target.is_relative_to(STORAGE_ROOT):
            return None
    except (OSError, ValueError):
        return None
    if target.is_file():
        return target
    # Media first downloaded on an older build may only exist in the flat cache.
    fallback = CACHE / path.replace("/", "_").replace("\\", "_")
    return fallback if fallback.is_file() else None


async def _rows(include_deleted: bool):
    where = "" if include_deleted else "WHERE is_deleted = FALSE"
    return await db.execute(
        f"SELECT storage_path, content_type, size FROM files {where} ORDER BY created_at",
        fetchall=True)


async def main(args) -> int:
    if not r2_storage.configured():
        print("R2 is not configured. Set R2_BUCKET, R2_ACCOUNT_ID, "
              "R2_ACCESS_KEY_ID and R2_SECRET_ACCESS_KEY, then re-run.")
        return 2

    if not os.environ.get("DATABASE_URL"):
        print("This migration targets the Postgres files table (DATABASE_URL unset).")
        return 2

    rows = await _rows(args.include_deleted)
    print(f"{len(rows)} object(s) recorded in the files table")
    print(f"r2 bucket : {r2_storage.bucket()}")
    print(f"endpoint  : {r2_storage.endpoint()}")
    print(f"prefix    : {r2_storage.prefix() or '(none)'}")
    print(f"mode      : {'APPLY' if args.apply else 'DRY RUN'}")
    print("-" * 68)

    uploaded = skipped = missing = failed = 0
    moved_bytes = 0

    for row in rows:
        if args.limit and uploaded >= args.limit:
            print(f"stopping after --limit {args.limit}")
            break
        path = row["storage_path"]
        local = _safe_local_path(path)
        if local is None:
            missing += 1
            print(f"  MISSING  {path}")
            continue
        try:
            if await asyncio.to_thread(r2_storage.exists, path):
                skipped += 1
                continue
        except Exception as exc:  # noqa: BLE001 - report and keep going
            failed += 1
            print(f"  HEAD FAIL {path}: {exc}")
            continue

        data = local.read_bytes()
        ctype = row.get("content_type") or mimetypes.guess_type(path)[0] or "application/octet-stream"
        if not args.apply:
            uploaded += 1
            moved_bytes += len(data)
            continue
        try:
            await asyncio.to_thread(r2_storage.upload, path, data, ctype)
        except Exception as exc:  # noqa: BLE001 - one bad object must not stop the run
            failed += 1
            print(f"  UPLOAD FAIL {path}: {exc}")
            continue
        if args.verify:
            try:
                back, _ = await asyncio.to_thread(r2_storage.download, path)
                if back != data:
                    failed += 1
                    print(f"  VERIFY MISMATCH {path}")
                    continue
            except Exception as exc:  # noqa: BLE001
                failed += 1
                print(f"  VERIFY FAIL {path}: {exc}")
                continue
        uploaded += 1
        moved_bytes += len(data)
        if uploaded % 25 == 0:
            print(f"  ... {uploaded} uploaded")

    print("-" * 68)
    print(f"uploaded : {uploaded}  ({moved_bytes / 1048576:.1f} MB)")
    print(f"skipped  : {skipped} (already in R2)")
    print(f"missing  : {missing} (no local copy)")
    print(f"failed   : {failed}")
    if not args.apply:
        print("\nDry run only. Re-run with --apply to upload.")
    elif uploaded:
        print("\nNext: restart the backend, then GET /api/ready should still return ok.")
        print("Keep the local files until R2 is proven; then archive them.")
    return 1 if failed else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="actually upload")
    parser.add_argument("--limit", type=int, default=0, help="stop after N uploads")
    parser.add_argument("--include-deleted", action="store_true",
                        help="also migrate soft-deleted rows")
    parser.add_argument("--verify", action="store_true",
                        help="download each object back and compare bytes")
    sys.exit(asyncio.run(main(parser.parse_args())))
