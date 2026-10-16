"""Regression guard: the forward runner must never select rollback SQL."""
from pathlib import Path

from backend.migrate import forward_migrations


def test_forward_runner_excludes_rollback_and_rehearsal(tmp_path: Path):
    for name in (
        "001_phase_zero.sql",
        "002_cloud_scene_job.sql",
        "002_cloud_scene_job.rollback.sql",
        "rehearsal_002_create.sql",
        "rehearsal_002_cleanup.sql",
    ):
        (tmp_path / name).write_text("SELECT 1;", encoding="utf-8")

    assert [path.name for path in forward_migrations(tmp_path)] == [
        "001_phase_zero.sql",
        "002_cloud_scene_job.sql",
    ]


def test_current_directory_never_selects_rollback():
    directory = Path(__file__).parents[1] / "migrations"
    selected = forward_migrations(directory)
    assert selected
    assert all(not path.name.endswith(".rollback.sql") for path in selected)
    assert "002_cloud_scene_job.rollback.sql" not in {path.name for path in selected}


def test_live_lease_sql_explicitly_targets_public_projects():
    directory = Path(__file__).parents[1] / "migrations"
    for name in ("002_cloud_scene_job.sql", "002_cloud_scene_job.rollback.sql"):
        statements = [line.strip() for line in (directory / name).read_text(encoding="utf-8").splitlines()
                      if line.strip() and not line.lstrip().startswith("--")]
        assert len(statements) == 2
        assert all(line.startswith("ALTER TABLE public.projects ") for line in statements)


def test_phase_zero_sql_uses_explicit_public_schema_and_no_default():
    sql = (Path(__file__).parents[1] / "migrations" / "001_phase_zero.sql").read_text(encoding="utf-8")
    statements = [line.strip() for line in sql.splitlines()
                  if line.strip() and not line.lstrip().startswith("--")]
    assert "SET LOCAL search_path = pg_catalog;" in statements
    assert all(line.startswith("ALTER TABLE public.") for line in statements if line.startswith("ALTER TABLE"))
    assert all(" ON public." in line for line in statements if line.startswith("CREATE INDEX"))
    assert "CREATE TABLE IF NOT EXISTS public.request_limits (" in statements
    assert " DEFAULT " not in sql.upper()
