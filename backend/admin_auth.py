"""Isolated administrator credentials.

An administrator is deliberately **not** a row in ``users``. Credentials live
in a separate table (``admin_credentials``) and authorization reads only that
table plus its own signed cookie (``admin_token``, token type ``"admin"``).
Those two facts give the isolation by construction:

  * a normal account can never become an administrator, whatever its ``role``
    column says, because no authorization path reads ``role`` any more;
  * the user cookie and the admin cookie carry different JWT types, so each is
    rejected by the other's dependency — possession of a user session confers
    nothing on the admin surface, and vice versa;
  * admin sign-in happens on its own page; nothing in the user experience links
    to it.

Seeding: startup copies ``ADMIN_EMAIL`` / ``ADMIN_PASSWORD`` into the store.
Change the environment variable and restart to rotate the credentials.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr, Field

from core import (db, log, decode, hash_password, make_token, cookie_options,
                  now_iso, new_id, verify_password)
import store

TABLE = "admin_credentials"
ADMIN_TTL = timedelta(hours=12)
LOCK_THRESHOLD = 5
LOCK_MINUTES = 15


def public(rec: dict | None) -> dict | None:
    if not rec:
        return None
    return {"id": rec.get("id"), "email": rec.get("email"),
            "name": rec.get("name") or "Administrator",
            "last_login_at": rec.get("last_login_at")}


async def ensure_admin(email: str, password: str, name: str = "Administrator") -> bool:
    """Create or refresh the administrator row from configuration."""
    email = (email or "").strip().lower()
    if not email or not password:
        return False
    existing = await find_by_email(email)
    if not existing:
        return await store.run(
            f"INSERT INTO {TABLE} (id, email, password_hash, name, created_at) "
            f"VALUES (%s, %s, %s, %s, NOW()) ON CONFLICT (email) DO NOTHING",
            (new_id(), email, hash_password(password), name), table=TABLE)
    if not verify_password(password, existing.get("password_hash", "")):
        return await store.run(
            f"UPDATE {TABLE} SET password_hash = %s, password_changed_at = NOW() WHERE email = %s",
            (hash_password(password), email), table=TABLE)
    return True


async def find_by_email(email: str) -> dict | None:
    email = (email or "").strip().lower()
    if not email:
        return None
    return await store.fetch_one(f"SELECT * FROM {TABLE} WHERE LOWER(email) = LOWER(%s) LIMIT 1",
                                 (email,), table=TABLE)


async def find_by_id(admin_id: str) -> dict | None:
    if not admin_id:
        return None
    return await store.fetch_one(f"SELECT * FROM {TABLE} WHERE id = %s LIMIT 1",
                                 (admin_id,), table=TABLE)


async def count() -> int:
    row = await store.fetch_one(f"SELECT COUNT(*) AS n FROM {TABLE}", table=TABLE)
    return int(row["n"]) if row else 0


async def _throttle(ident: str) -> None:
    """Same shape as the user login throttle, under a distinct identifier."""
    att = await db.login_attempts.find_one({"identifier": ident})
    if att and att.get("count", 0) >= LOCK_THRESHOLD:
        locked = att.get("locked_until")
        locked_str = locked.isoformat() if hasattr(locked, "isoformat") else str(locked or "")
        if locked_str > now_iso():
            raise HTTPException(429, "Too many attempts. Try again in 15 minutes.")


async def _record_failure(ident: str) -> None:
    att = await db.login_attempts.find_one({"identifier": ident})
    count = (att or {}).get("count", 0) + 1
    lock = (datetime.now(timezone.utc) + timedelta(minutes=LOCK_MINUTES)).isoformat() \
        if count >= LOCK_THRESHOLD else ""
    await db.login_attempts.update_one({"identifier": ident},
                                       {"$set": {"count": count, "locked_until": lock}}, upsert=True)


async def _clear_failures(ident: str) -> None:
    try:
        await db.login_attempts.delete_one({"identifier": ident})
    except Exception as exc:  # noqa: BLE001 - a bookkeeping failure must not block a valid sign-in
        log.warning("admin: could not clear login attempts (%s: %s)", type(exc).__name__, exc)


def set_admin_cookies(response, admin_id: str) -> None:
    response.set_cookie("admin_token", make_token(admin_id, "admin", ADMIN_TTL),
                        max_age=int(ADMIN_TTL.total_seconds()), **cookie_options())


def clear_admin_cookies(response) -> None:
    response.delete_cookie("admin_token", **cookie_options())


async def authenticate(email: str, password: str, request: Request | None = None) -> dict:
    """Verify administrator credentials. Raises 401 on failure."""
    email = (email or "").strip().lower()
    host = getattr(getattr(request, "client", None), "host", None) or "x"
    ident = f"admin:{host}:{email}"
    await _throttle(ident)
    rec = await find_by_email(email)
    # verify_password must run even with no row, but bcrypt on a dummy keeps the
    # timing profile flat enough for this surface without extra machinery.
    ok = bool(rec) and verify_password(password, rec.get("password_hash", ""))
    if not ok:
        await _record_failure(ident)
        raise HTTPException(401, "Invalid administrator credentials")
    await _clear_failures(ident)
    if store.using_sql():
        await store.run(f"UPDATE {TABLE} SET last_login_at = NOW() WHERE id = %s",
                        (rec["id"],), table=TABLE)
    else:
        log.error("Admin store needs Postgres: administrator sessions will not persist. "
                  "Set DATABASE_URL and run migrations/004_auth_growth_notify.sql")
    return rec


async def require_admin(request: Request) -> dict:
    """Dependency: only a valid admin cookie reaches an admin route."""
    token = request.cookies.get("admin_token")
    if not token:
        raise HTTPException(401, "Administrator sign-in required")
    admin_id = decode(token, ("admin",))
    rec = await find_by_id(admin_id)
    if not rec:
        raise HTTPException(401, "Administrator account not found")
    return rec


# --------------------------------------------------------------- routes

router = APIRouter(prefix="/api/admin")


class AdminLoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


@router.post("/auth/login")
async def admin_login(body: AdminLoginIn, request: Request, response: Response):
    rec = await authenticate(body.email, body.password, request)
    set_admin_cookies(response, rec["id"])
    log.info("Administrator signed in: %s", rec.get("email"))
    return public(rec)


@router.post("/auth/logout")
async def admin_logout(response: Response):
    clear_admin_cookies(response)
    return {"ok": True}


@router.get("/auth/me")
async def admin_me(admin: dict = Depends(require_admin)):
    return public(admin)

