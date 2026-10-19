"""What a user is allowed to do right now.

One place resolves plan, quota and expiry so the render gate, the pricing page
and the admin dashboard cannot disagree about someone's limits.
"""
from __future__ import annotations

from datetime import datetime, timezone

import billing
import billing_store


def _as_dt(value):
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if not value:
        return None
    try:
        text = str(value).replace("Z", "+00:00")
        parsed = datetime.fromisoformat(text)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


async def entitlement(user: dict) -> dict:
    """Resolve the effective plan, quota and remaining allowance for a user.

    A paid plan whose period has ended drops back to free automatically. That is
    done by reading the row, not by a scheduled job, so the downgrade is always
    correct even if a webhook is missed.
    """
    user = user or {}
    user_id = user.get("id") or ""
    sub = await billing_store.get_subscription(user_id) or {}

    plan_id = sub.get("plan") or user.get("plan") or "free"
    status = sub.get("status") or "active"
    ends_at = _as_dt(sub.get("current_period_end"))
    now = datetime.now(timezone.utc)

    expired = bool(ends_at and ends_at <= now)
    paid = billing.plan(plan_id).get("tier", 0) > 0
    if paid and (expired or status in ("cancelled", "expired")):
        # Cancelled plans keep access until the period they paid for ends.
        if expired or status == "expired":
            plan_id, status = "free", "expired"
        elif status == "cancelled":
            status = "cancelled"

    videos, period, max_seconds = billing.quota_for(plan_id)
    period_key = billing.period_key(period)
    since = billing.period_start(period)
    used = await billing_store.usage(user_id, period, period_key, since)

    detail = billing.describe(plan_id, (sub.get("currency") or user.get("currency") or "USD").upper())
    return {
        "user_id": user_id,
        "plan": plan_id,
        "plan_name": detail["name"],
        "status": status,
        "tier": detail["tier"],
        "videos_allowed": videos,
        "videos_used": used,
        "videos_remaining": max(videos - used, 0),
        "period": period,
        "period_label": detail["period_label"],
        "period_key": period_key,
        "resets_at": billing.period_reset(period),
        "max_seconds": max_seconds,
        "provider": sub.get("provider") or "",
        "currency": (sub.get("currency") or "USD").upper(),
        "interval": sub.get("interval") or "month",
        "renews_at": ends_at.isoformat() if ends_at else "",
        "checkout_ready": billing.provider_configured((sub.get("currency") or "USD")),
    }


async def can_render(user: dict, seconds: int | None = None) -> tuple[bool, str, dict]:
    """(allowed, reason, entitlement). Reason is shown to the creator verbatim."""
    ent = await entitlement(user)
    if seconds and int(seconds) > ent["max_seconds"]:
        return (False,
                f"The {ent['plan_name']} plan makes videos up to {ent['max_seconds']} seconds. "
                f"Upgrade to render a {int(seconds)} second story.", ent)
    if ent["videos_remaining"] <= 0:
        return (False,
                f"You have used all {ent['videos_allowed']} videos on the {ent['plan_name']} plan "
                f"this {ent['period_label']}. It resets on "
                f"{ent['resets_at'][:10]}. Upgrade for more videos now.", ent)
    return True, "", ent


async def record_render(user_id: str) -> None:
    """Count a finished video against the user's current quota window.

    Called when a render completes, not when it starts, so a failed render never
    consumes the creator's allowance. When the counter table is absent the count
    is derived from completed project rows, which now include this one.
    """
    if not user_id:
        return
    from core import db  # local import avoids a cycle at module load
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        return
    ent = await entitlement(user)
    await billing_store.add_usage(user_id, ent["period_key"])
