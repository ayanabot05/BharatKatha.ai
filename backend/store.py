"""Fail-soft SQL helpers for the auth / analytics / early-access stores.

These stores are Postgres-only, exactly like ``billing_store``: the Mongo
backend predates billing and is not a deployment target. When the process
cannot run SQL, every helper here reports "no data" instead of raising, which
means:

  * administrator sign-in is **denied** (fails closed, never open),
  * password reset is reported as unavailable,
  * analytics simply records nothing.

Nothing in this module raises for a missing table, so forgetting to run
``migrate.py`` can never break login, signup or rendering. A missing table is
remembered and never queried again, so logs stay quiet.
"""
from __future__ import annotations

from core import db, log

_MISSING_MARKERS = ("does not exist", "undefinedtable", "42p01",
                    "undefined table", "undefined column", "42703")

# Tables discovered to be absent. Reported once, then skipped.
_missing: set[str] = set()


def using_sql() -> bool:
    """True when the configured backend can run SQL (Postgres)."""
    return hasattr(db, "execute")


def unavailable(table: str) -> bool:
    return table in _missing


def _note_missing(exc: Exception, table: str | None) -> bool:
    if not table:
        return False
    text = str(exc).lower()
    if any(marker in text for marker in _MISSING_MARKERS):
        if table not in _missing:
            _missing.add(table)
            log.warning("store: table %s is unavailable; run migrations/004_auth_growth_notify.sql",
                        table)
        return True
    return False


async def fetch_one(query, params=(), table: str | None = None) -> dict | None:
    """One row as a dict, or None when absent/unavailable."""
    if not using_sql() or (table and table in _missing):
        return None
    try:
        row = await db.execute(query, params, fetchone=True)
    except Exception as exc:  # noqa: BLE001 - storage must degrade, not crash
        if not _note_missing(exc, table):
            log.warning("store: fetch_one failed (%s: %s)", type(exc).__name__, exc)
        return None
    return dict(row) if row else None


async def fetch_all(query, params=(), table: str | None = None) -> list:
    """Rows as a list of dicts; empty when absent/unavailable."""
    if not using_sql() or (table and table in _missing):
        return []
    try:
        rows = await db.execute(query, params, fetchall=True)
    except Exception as exc:  # noqa: BLE001
        if not _note_missing(exc, table):
            log.warning("store: fetch_all failed (%s: %s)", type(exc).__name__, exc)
        return []
    return [dict(r) for r in (rows or [])]


async def run(query, params=(), table: str | None = None) -> bool:
    """Execute a write. True when the statement ran without error.

    This is deliberately distinct from "a row came back": an INSERT without
    RETURNING yields no rows on success, so callers must not infer failure from
    an empty result (an earlier helper in this codebase did exactly that and
    reported successful writes as failed).
    """
    if not using_sql() or (table and table in _missing):
        return False
    try:
        await db.execute(query, params)
    except Exception as exc:  # noqa: BLE001
        if not _note_missing(exc, table):
            log.warning("store: write failed (%s: %s)", type(exc).__name__, exc)
        return False
    return True
