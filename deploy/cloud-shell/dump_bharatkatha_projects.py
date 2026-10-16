"""Prepared only: dump BharatKatha public.projects without putting its URL in argv.

Reads the PostgreSQL URL from stdin, never prints it, and writes a mode-0600
custom-format archive. This script does not connect unless explicitly run.
"""
import hashlib
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse


PROJECT_REF = "nnytovnsypegvrdilqks"


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: dump_bharatkatha_projects.py /private/path/projects.dump")
    parsed = urlparse(sys.stdin.readline().strip())
    user = unquote(parsed.username or "")
    if parsed.scheme not in {"postgres", "postgresql"} or not parsed.hostname:
        raise SystemExit("A PostgreSQL URL is required on stdin")
    if parsed.hostname != f"db.{PROJECT_REF}.supabase.co" and user.split(".")[-1] != PROJECT_REF:
        raise SystemExit("Refusing a database outside BharatKatha Supabase")
    destination = Path(sys.argv[1])
    if not destination.parent.is_dir():
        raise SystemExit("Create a private destination directory first")
    fd = os.open(destination, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(fd)
    env = os.environ.copy()
    env.update(PGHOST=parsed.hostname, PGPORT=str(parsed.port or 5432),
               PGUSER=user, PGDATABASE=parsed.path.lstrip("/") or "postgres",
               PGPASSWORD=unquote(parsed.password or ""), PGSSLMODE="require",
               PGCONNECT_TIMEOUT="10")
    try:
        subprocess.run(["pg_dump", "--no-password", "--format=custom",
                        "--table=public.projects", f"--file={destination}"],
                       env=env, check=True, timeout=1800)
        subprocess.run(["pg_restore", "--list", str(destination)],
                       stdout=subprocess.DEVNULL, check=True, timeout=30)
    except Exception:
        destination.unlink(missing_ok=True)
        raise SystemExit("Dump or archive listing failed; inspect privately") from None
    hasher = hashlib.sha256()
    with destination.open("rb") as archive:
        for chunk in iter(lambda: archive.read(1024 * 1024), b""):
            hasher.update(chunk)
    digest = hasher.hexdigest()
    print(f"Archive created: {destination}; SHA-256: {digest}")
    print("Archive listing succeeded; RESTORE IS NOT YET VERIFIED")


if __name__ == "__main__":
    main()
