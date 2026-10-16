"""Apply reviewed, idempotent Phase 0 migrations using backend-only credentials."""
import os
from pathlib import Path
import psycopg2
from dotenv import load_dotenv


def forward_migrations(directory: Path) -> list[Path]:
    """Select numbered forward scripts; never execute companion rollback files."""
    return [path for path in sorted(directory.glob("[0-9][0-9][0-9]_*.sql"))
            if not path.name.endswith(".rollback.sql")]


def main():
    root = Path(__file__).parent
    load_dotenv(root / ".env")
    with psycopg2.connect(os.environ["DATABASE_URL"], connect_timeout=10) as conn:
        with conn.cursor() as cursor:
            for path in forward_migrations(root / "migrations"):
                cursor.execute(path.read_text(encoding="utf-8"))
                print(f"Applied {path.name}")


if __name__ == "__main__":
    main()
