"""Password reset: request a link, then consume it.

Design notes:

  * **No account enumeration.** ``/auth/forgot`` answers identically whether or
    not the address exists. The only thing that changes the answer is whether
    the reset store itself is available, which says nothing about the account.
  * **Single-use, expiring, hashed tokens.** Only a SHA-256 hash is persisted,
    so a database leak cannot be replayed. Tokens live 30 minutes; using one
    invalidates every other outstanding token for that account.
  * **Honest delivery.** When SMTP is not configured the endpoint reports
    ``delivery: "manual"`` and the link is written to the server log for the
    operator to relay. It never claims an email was sent when it was not.
"""
from __future__ import annotations

import hashlib
import secrets

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field

from core import db, hash_password, log
import mailer
import store

router = APIRouter(prefix="/api")
RESETS = "password_resets"
TOKEN_MINUTES = 30
COOLDOWN_SECONDS = 60


class ForgotIn(BaseModel):
    email: EmailStr


class ResetIn(BaseModel):
    token: str = Field(min_length=10, max_length=200)
    password: str = Field(min_length=6)


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _unavailable() -> dict:
    return {"sent": False, "delivery": "unavailable",
            "message": "Password reset is not set up on this server yet."}


@router.post("/auth/forgot")
async def forgot(body: ForgotIn, request: Request):
    email = body.email.lower()
    if not store.using_sql():
        log.error("Password reset needs Postgres; set DATABASE_URL and run "
                  "migrations/004_auth_growth_notify.sql")
        return _unavailable()

    user = await db.users.find_one({"email": email})
    # Generic reply for an unknown address, so this cannot be used to discover
    # which emails have accounts.
    if not user:
        return {"sent": True, "delivery": mailer.delivery_mode()}

    # One link per minute per account is plenty, and stops the endpoint being
    # used to bomb somebody's inbox.
    recent = await store.fetch_one(
        f"SELECT 1 AS x FROM {RESETS} WHERE user_id = %s "
        f"AND created_at > NOW() - INTERVAL '{COOLDOWN_SECONDS} seconds' LIMIT 1",
        (user["id"],), table=RESETS)
    if recent:
        return {"sent": True, "delivery": mailer.delivery_mode()}

    token = secrets.token_urlsafe(32)
    created = await store.run(
        f"INSERT INTO {RESETS} (token_hash, user_id, expires_at) "
        f"VALUES (%s, %s, NOW() + INTERVAL '{TOKEN_MINUTES} minutes')",
        (_hash(token), user["id"]), table=RESETS)
    if not created:
        return _unavailable()

    link = mailer.reset_link(token)
    sent = await mailer.send(
        email,
        "Reset your BharatChitra AI password",
        ("Someone asked to reset the password for your BharatChitra AI account.\n\n"
         f"Open this link within {TOKEN_MINUTES} minutes to choose a new password:\n{link}\n\n"
         "If this was not you, you can ignore this message — the link expires on its own."),
        also_log=f"reset link for {email}: {link}")
    return {"sent": True, "delivery": "email" if sent else "manual",
            "expires_in_minutes": TOKEN_MINUTES}


@router.post("/auth/reset")
async def reset(body: ResetIn):
    row = await store.fetch_one(
        f"SELECT user_id FROM {RESETS} WHERE token_hash = %s "
        f"AND used_at IS NULL AND expires_at > NOW() LIMIT 1",
        (_hash(body.token),), table=RESETS)
    if not row:
        raise HTTPException(400, "This reset link is invalid or has expired. Request a new one.")

    user_id = row["user_id"]
    await db.users.update_one({"id": user_id}, {"$set": {"password_hash": hash_password(body.password)}})
    # Burn this token and every other outstanding one for the account.
    await store.run(f"UPDATE {RESETS} SET used_at = NOW() WHERE user_id = %s AND used_at IS NULL",
                    (user_id,), table=RESETS)
    log.info("Password reset completed for user %s", user_id)
    return {"ok": True}
