"""Static safety check; this does not execute SQL or verify DB privileges."""
import re
from pathlib import Path


ROOT = Path(__file__).parents[1] / "migrations"
SCHEMA = "bk_lease_rehearsal_20261016"


def statements(name: str) -> list[str]:
    sql = (ROOT / name).read_text(encoding="utf-8")
    sql = "\n".join(line.split("--", 1)[0] for line in sql.splitlines())
    return [re.sub(r"\s+", " ", part).strip().lower()
            for part in sql.split(";") if part.strip()]


def test_create_writes_only_to_fixed_rehearsal_schema():
    parts = statements("rehearsal_002_create.sql")
    assert parts == [
        "begin",
        "set local lock_timeout = '3s'",
        "set local statement_timeout = '30s'",
        "set local search_path = pg_catalog",
        f"create schema {SCHEMA}",
        f"create table {SCHEMA}.projects (like public.projects)",
        f"alter table {SCHEMA}.projects add column if not exists scene_job_started_at timestamptz",
        f"alter table {SCHEMA}.projects add column if not exists scene_job_token text",
        "commit",
        "select column_name, data_type from information_schema.columns where table_schema = 'bk_lease_rehearsal_20261016' and table_name = 'projects' and column_name in ('id','user_id','scenes','render','scene_job_started_at','scene_job_token') order by column_name",
        f"select count(*) as rehearsal_rows from {SCHEMA}.projects",
    ]
    assert "cascade" not in " ".join(parts)


def test_cleanup_only_drops_rehearsal_objects_without_cascade():
    parts = statements("rehearsal_002_cleanup.sql")
    assert parts == [
        "begin",
        "set local lock_timeout = '3s'",
        "set local statement_timeout = '30s'",
        "set local search_path = pg_catalog",
        f"drop table {SCHEMA}.projects",
        f"drop schema {SCHEMA}",
        "commit",
    ]
    assert "cascade" not in " ".join(parts)
