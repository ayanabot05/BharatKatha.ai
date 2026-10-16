"""Static safeguards for the restored-cluster migration 002 rehearsal."""
from pathlib import Path


MIGRATIONS = Path(__file__).parents[1] / "migrations"


def test_rehearsal_uses_exact_forward_migration_and_always_rolls_back():
    sql = (MIGRATIONS / "rehearsal_local_002_transaction.sql").read_text(encoding="utf-8")
    assert "\\ir 002_cloud_scene_job.sql" in sql
    assert "ROLLBACK;" in sql
    assert "COMMIT;" not in sql.upper()
    assert sql.index("$guard$;") < sql.index("\\ir 002_cloud_scene_job.sql")
    assert sql.index("$verify$;") < sql.index("ROLLBACK;")
    assert "lease_columns_after_rollback" in sql


def test_rehearsal_refuses_other_database_or_network_connection():
    sql = (MIGRATIONS / "rehearsal_local_002_transaction.sql").read_text(encoding="utf-8")
    for expected in (
        "current_database() <> 'bharatkatha_restore_test'",
        "current_setting('port') <> '5433'",
        "inet_server_addr() IS NOT NULL",
        "current_setting('server_version_num')::int NOT BETWEEN 170000 AND 179999",
        "'/17/bharatkatha_test'",
        "to_regclass('public.projects') IS NULL",
        "CREATE TEMP TABLE pg_temp.bk002_baseline ON COMMIT DROP",
    ):
        assert expected in sql
    assert "supabase.co" not in sql.lower()
    assert "postgresql://" not in sql.lower()


def test_rehearsal_inventory_is_read_only_and_qualified():
    sql = (MIGRATIONS / "rehearsal_local_002_preflight.sql").read_text(encoding="utf-8")
    assert "BEGIN TRANSACTION READ ONLY;" in sql
    assert "SET LOCAL search_path = pg_catalog;" in sql
    assert "FROM public.projects AS p" in sql
    assert "FROM information_schema.columns" in sql
    assert "FROM pg_indexes" in sql
    assert "FROM pg_constraint" in sql
    assert "ROLLBACK;" in sql


def test_forward_selector_ignores_local_rehearsal_files():
    from backend.migrate import forward_migrations

    selected = {path.name for path in forward_migrations(MIGRATIONS)}
    assert "rehearsal_local_002_preflight.sql" not in selected
    assert "rehearsal_local_002_transaction.sql" not in selected
