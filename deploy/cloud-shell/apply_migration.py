"""Apply the reviewed scene lease migration using a DB URL supplied on stdin.

Use only after explicit deployment approval and a safe Supabase schema rehearsal.
Never prints the URL or any secret value.
"""

import os
import sys
from pathlib import Path
from urllib.parse import urlparse

import psycopg2


def main():
    if os.environ.get("BHARATKATHA_LIVE_MIGRATION_APPROVED") != "yes":
        raise SystemExit("Explicit live migration approval is required")
    if os.environ.get("BHARATKATHA_BACKUP_VERIFIED") != "yes":
        raise SystemExit("Verify a restorable BharatKatha backup first")
    url = sys.stdin.read().strip()
    parsed = urlparse(url)
    if parsed.scheme not in {"postgres", "postgresql"} or not parsed.hostname:
        raise SystemExit("A PostgreSQL URL is required on stdin")
    project_ref = "nnytovnsypegvrdilqks"
    supplied_ref = (parsed.username or "").split(".")[-1]
    direct_host = parsed.hostname == f"db.{project_ref}.supabase.co"
    if supplied_ref != project_ref and not direct_host:
        raise SystemExit("Refusing a database outside the configured BharatKatha Supabase project")
    sql = (Path(__file__).parents[2] / "backend" / "migrations" / "002_cloud_scene_job.sql").read_text()
    try:
        with psycopg2.connect(url, connect_timeout=10) as conn:
            with conn.cursor() as cur:
                cur.execute("SET LOCAL lock_timeout = '3s'")
                cur.execute("SET LOCAL statement_timeout = '30s'")
                cur.execute("SET LOCAL search_path = pg_catalog")
                cur.execute(sql)
                cur.execute("SELECT scene_job_started_at, scene_job_token FROM public.projects LIMIT 0")
    except Exception as exc:
        raise SystemExit(f"Migration failed ({type(exc).__name__}); inspect the DB privately") from None
    print("Migration 002 applied and columns verified")


if __name__ == "__main__":
    main()
