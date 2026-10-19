"""Early-access sign-ups ("notify me") for features that are not live yet.

Used by the landing page's honest *coming soon* section for full AI video
motion. A sign-up is only reported as saved when it was actually persisted;
when the store is unavailable the caller says so instead of showing a success
message for a request that went nowhere.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr, Field

from core import log, new_id
import store
from admin_auth import require_admin

TABLE = "notify_signups"
TOPICS = {"ai_motion"}


class NotifyIn(BaseModel):
    email: EmailStr
    topic: str = Field(default="ai_motion", max_length=40)
    source: str = Field(default="landing", max_length=80)
    note: str = Field(default="", max_length=500)


router = APIRouter(prefix="/api")
admin_router = APIRouter(prefix="/api/admin")


@router.post("/notify")
async def notify(body: NotifyIn):
    topic = body.topic if body.topic in TOPICS else "ai_motion"
    email = body.email.strip().lower()
    row = await store.fetch_one(
        f"INSERT INTO {TABLE} (id, email, topic, source, note) "
        f"VALUES (%s, %s, %s, %s, %s) "
        f"ON CONFLICT (email, topic) DO NOTHING RETURNING id",
        (new_id(), email, topic, body.source, body.note.strip()[:500]), table=TABLE)
    if row:
        return {"saved": True, "already": False}
    if not store.using_sql() or store.unavailable(TABLE):
        log.error("Early-access sign-ups need Postgres; set DATABASE_URL and run "
                  "migrations/004_auth_growth_notify.sql")
        return {"saved": False, "already": False,
                "message": "We could not save that just now. Please try again later."}
    # The insert was rejected by the unique key: they are already on the list.
    return {"saved": True, "already": True}


@admin_router.get("/signups")
async def list_signups(topic: str = "", limit: int = 100, _: dict = Depends(require_admin)):
    limit = max(1, min(int(limit or 100), 500))
    if topic:
        rows = await store.fetch_all(
            f"SELECT id, email, topic, source, note, created_at FROM {TABLE} "
            f"WHERE topic = %s ORDER BY created_at DESC LIMIT %s",
            (topic, limit), table=TABLE)
    else:
        rows = await store.fetch_all(
            f"SELECT id, email, topic, source, note, created_at FROM {TABLE} "
            f"ORDER BY created_at DESC LIMIT %s", (limit,), table=TABLE)
    return {"count": len(rows), "signups": rows,
            "tables_ready": not store.unavailable(TABLE)}
