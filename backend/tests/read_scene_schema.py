"""Read-only actual Supabase projects column names/types; never prints credentials."""

import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

load_dotenv(Path(__file__).parents[1] / ".env")
url = os.environ.get("DATABASE_URL")
if not url:
    raise SystemExit("DATABASE_URL unavailable")
try:
    with psycopg2.connect(url, connect_timeout=6) as conn:
        with conn.cursor() as cur:
            cur.execute("SET TRANSACTION READ ONLY")
            cur.execute("""SELECT column_name, data_type FROM information_schema.columns
                WHERE table_name = 'projects' AND column_name IN
                ('id','user_id','scenes','render','scene_job_started_at','scene_job_token')
                ORDER BY column_name""")
            print(cur.fetchall())
except Exception as exc:
    raise SystemExit(f"Read-only schema check failed ({type(exc).__name__})") from None
