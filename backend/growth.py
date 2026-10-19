"""First-party product analytics.

Events are recorded **in this database**, not sent to a third-party script, so
the funnel is complete (ad blockers and cookie consent cannot punch holes in it)
and the data never leaves the deployment.

The funnel is the one that actually describes this product:

    visit -> signup -> project_created -> script_approved -> render_completed -> download

``visit`` is the only event the browser is allowed to report (the landing page
cannot know anything else first-hand). Every other stage is written by the
server inside the handler that performs the action, so it cannot be forged by a
client and cannot be missed by a blocked beacon.

Like the other newer stores this is Postgres-only and fail-soft: if the table is
absent, tracking records nothing and the dashboard says so, rather than
inventing numbers.
"""
from __future__ import annotations

import asyncio
import json
import os

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from core import current_user, log, now_iso
import store
from admin_auth import require_admin

TABLE = "growth_events"

# Ordered funnel. Names are the contract between the writers and the dashboard.
FUNNEL = ["visit", "signup", "project_created", "script_approved",
          "render_completed", "download"]

STAGE_LABELS = {
    "visit": "Landing visits",
    "signup": "Sign-ups",
    "project_created": "Stories started",
    "script_approved": "Scripts approved",
    "render_completed": "Videos rendered",
    "download": "Downloads",
}

# The only event a client is allowed to report about itself.
CLIENT_EVENTS = {"visit"}


def _window(days: int) -> int:
    return max(1, min(int(days or 30), 365))


def _suppressed() -> bool:
    """True while the test suite is running.

    Tests exercise the real render and download handlers with faked storage, so
    without this they would write fixture events ("owner-1", "story-1") straight
    into the live funnel and make the numbers wrong. Analytics is the one thing
    that must never leak out of a test run.
    """
    return bool(os.environ.get("PYTEST_CURRENT_TEST")) or os.environ.get("APP_ENV") == "test"


async def track(name: str, user_id: str | None = None, session_id: str = "", **props) -> None:
    """Record one event. Never raises, never blocks a request on failure."""
    if not name or _suppressed():
        return
    try:
        await store.run(
            f"INSERT INTO {TABLE} (user_id, session_id, name, props) VALUES (%s, %s, %s, %s)",
            (user_id or None, session_id or "", name,
             json.dumps(props or {}, ensure_ascii=False, default=str)),
            table=TABLE)
    except Exception as exc:  # noqa: BLE001 - analytics must never break a request
        log.warning("growth: could not record %s (%s: %s)", name, type(exc).__name__, exc)


# --------------------------------------------------------------- reporting

async def _counts(days: int, unique: bool = False) -> dict:
    expr = "COUNT(DISTINCT user_id)" if unique else "COUNT(*)"
    rows = await store.fetch_all(
        f"SELECT name, {expr} AS n FROM {TABLE} "
        f"WHERE created_at >= NOW() - INTERVAL '{days} days' GROUP BY name", table=TABLE)
    return {r["name"]: int(r["n"] or 0) for r in rows}


def _pct(part: int, whole: int):
    if not whole:
        return None
    return round(part * 100.0 / whole, 1)


async def funnel(days: int = 30) -> dict:
    """Ordered funnel with conversion against the previous stage and the top."""
    days = _window(days)
    events, people = await asyncio.gather(_counts(days), _counts(days, unique=True))
    top = events.get(FUNNEL[0], 0)

    stages, previous = [], None
    for name in FUNNEL:
        count = events.get(name, 0)
        stages.append({
            "name": name,
            "label": STAGE_LABELS.get(name, name),
            "events": count,
            "people": people.get(name, 0),
            "from_previous_pct": None if previous is None else _pct(count, previous),
            "from_top_pct": _pct(count, top),
        })
        previous = count

    return {"days": days, "stages": stages,
            "available": store.using_sql(),
            "tables_ready": not store.unavailable(TABLE)}


async def daily(days: int = 30) -> dict:
    """Per-day counts for each funnel stage, for the dashboard trend."""
    days = _window(days)
    rows = await store.fetch_all(
        f"SELECT to_char(date_trunc('day', created_at), 'YYYY-MM-DD') AS day, "
        f"name, COUNT(*) AS n FROM {TABLE} "
        f"WHERE created_at >= NOW() - INTERVAL '{days} days' "
        f"GROUP BY 1, 2 ORDER BY 1", table=TABLE)
    series: dict = {}
    for r in rows:
        series.setdefault(r["day"], {})[r["name"]] = int(r["n"] or 0)
    return {"days": days, "series": series}


# --------------------------------------------------------------- routes

class EventIn(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    session_id: str = Field(default="", max_length=64)
    path: str = Field(default="", max_length=200)


router = APIRouter(prefix="/api")
admin_router = APIRouter(prefix="/api/admin")


@router.post("/events")
async def ingest(body: EventIn, request: Request):
    """Client-reported events, restricted to a tiny allowlist."""
    if body.name not in CLIENT_EVENTS:
        return {"ok": False, "reason": "unknown event"}
    user_id = None
    if request.cookies.get("access_token"):
        try:
            user_id = (await current_user(request)).get("id")
        except Exception:  # expired or bogus cookie: still count the visit
            user_id = None
    await track(body.name, user_id=user_id, session_id=body.session_id, path=body.path)
    return {"ok": True}


@admin_router.get("/growth")
async def admin_growth(days: int = 30, _: dict = Depends(require_admin)):
    f, d = await asyncio.gather(funnel(days), daily(days))
    return {"funnel": f, "daily": d, "generated_at": now_iso()}
