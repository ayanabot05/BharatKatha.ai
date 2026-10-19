"""Persistence for billing, quota, payments and admin actions.

Deliberately fail-soft. Until migrations/003_billing.sql is applied, the new
tables do not exist; that must not break signup, rendering or login. Every read
degrades to an empty result and every write is reported as not-persisted, and
the caller decides what is safe to do without it.

Quota specifically does NOT depend on a new table: videos produced in the
current window are counted from public.projects, which already exists
(render->>'status' = 'done'), so the free weekly allowance is enforceable on day
one. The render_usage counter is used only once it exists.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from core import db, log, new_id, now_iso

# Tables known to be missing. Discovered once, then never queried again, so a
# deployment without the billing migration does not log on every request.
_missing: set[str] = set()

_MISSING_MARKERS = ("does not exist", "undefinedtable", "42p01", "undefined table")


def unavailable(table: str) -> bool:
    return table in _missing


async def _query(sql, params=(), fetchone=False, fetchall=False, commit=True, table=None):
    """Run a query, returning None/[] instead of raising when a table is absent."""
    if table and table in _missing:
        return None if fetchone else []
    try:
        return await db.execute(sql, params, fetchone=fetchone, fetchall=fetchall, commit=commit)
    except Exception as exc:  # noqa: BLE001 - any storage failure must degrade, not crash
        text = str(exc).lower()
        if table and any(marker in text for marker in _MISSING_MARKERS):
            _missing.add(table)
            log.warning("billing: table %s is unavailable; run migrations/003_billing.sql "
                        "(degrading gracefully)", table)
        else:
            log.warning("billing: query failed (%s: %s)", type(exc).__name__, exc)
        return None if fetchone else []


# --------------------------------------------------------------- subscriptions

async def get_subscription(user_id: str) -> dict | None:
    if not user_id:
        return None
    return await _query("SELECT * FROM subscriptions WHERE user_id = %s LIMIT 1",
                        (user_id,), fetchone=True, table="subscriptions")


async def upsert_subscription(user_id: str, **fields) -> bool:
    """Create or update a user's entitlement. Returns True when persisted."""
    if not user_id:
        return False
    allowed = ("plan", "status", "provider", "currency", "interval",
               "provider_customer_id", "provider_subscription_id", "current_period_end")
    sets = {k: v for k, v in fields.items() if k in allowed}
    if not sets:
        return False
    cols = ", ".join(sets)
    placeholders = ", ".join(["%s"] * len(sets))
    updates = ", ".join(f"{k} = EXCLUDED.{k}" for k in sets)
    # RETURNING matters: an INSERT without it yields no rows on success, so
    # "no row" would be misread as "not persisted".
    sql = (f"INSERT INTO subscriptions (user_id, {cols}, updated_at) "
           f"VALUES (%s, {placeholders}, NOW()) "
           f"ON CONFLICT (user_id) DO UPDATE SET {updates}, updated_at = NOW() "
           f"RETURNING user_id")
    result = await _query(sql, (user_id, *sets.values()), fetchone=True,
                          table="subscriptions")
    return result is not None


# --------------------------------------------------------------- usage / quota

async def counter_value(user_id: str, period_key: str) -> int | None:
    """Usage from the dedicated counter, or None when the counter is unavailable."""
    row = await _query("SELECT used FROM render_usage WHERE user_id = %s AND period_key = %s",
                       (user_id, period_key), fetchone=True, table="render_usage")
    if isinstance(row, dict):
        return int(row.get("used") or 0)
    return None


async def videos_since(user_id: str, since: datetime) -> int:
    """Rendered videos in the window, counted from existing project rows.

    This is the fallback that makes the free allowance real without a migration.
    """
    row = await _query(
        "SELECT COUNT(*) AS n FROM projects "
        "WHERE user_id = %s AND render->>'status' = 'done' AND updated_at >= %s",
        (user_id, since), fetchone=True)
    if isinstance(row, dict):
        return int(row.get("n") or 0)
    return 0


async def usage(user_id: str, period: str, period_key: str, since: datetime) -> int:
    counted = await counter_value(user_id, period_key)
    if counted is not None:
        return counted
    return await videos_since(user_id, since)


async def add_usage(user_id: str, period_key: str) -> int:
    """Increment the counter. Returns the value in use after this call.

    When the counter table is absent we fall back to the project count, which
    already includes this render once it is marked done.
    """
    row = await _query(
        "INSERT INTO render_usage (user_id, period_key, used, updated_at) "
        "VALUES (%s, %s, 1, NOW()) "
        "ON CONFLICT (user_id, period_key) DO UPDATE SET used = render_usage.used + 1, updated_at = NOW() "
        "RETURNING used",
        (user_id, period_key), fetchone=True, table="render_usage")
    if isinstance(row, dict):
        return int(row.get("used") or 1)
    return 0


# --------------------------------------------------------------- payments

async def record_payment(**fields) -> bool:
    allowed = ("id", "user_id", "email", "provider", "provider_payment_id", "provider_order_id",
               "plan", "interval", "currency", "amount", "status", "raw")
    row = {k: v for k, v in fields.items() if k in allowed}
    row.setdefault("id", new_id())
    if row.get("raw") is not None and not isinstance(row["raw"], str):
        row["raw"] = json.dumps(row["raw"], ensure_ascii=False, default=str)
    cols = ", ".join(row)
    placeholders = ", ".join(["%s"] * len(row))
    result = await _query(
        f"INSERT INTO payments ({cols}, updated_at) VALUES ({placeholders}, NOW()) "
        f"ON CONFLICT (id) DO NOTHING RETURNING id", tuple(row.values()),
        fetchone=True, table="payments")
    return result is not None


async def update_payment_by_provider_id(provider: str, provider_payment_id: str, **fields) -> None:
    allowed = ("status", "user_id", "plan", "interval", "currency", "amount", "email", "raw")
    sets = {k: v for k, v in fields.items() if k in allowed}
    if not sets:
        return
    if sets.get("raw") is not None and not isinstance(sets["raw"], str):
        sets["raw"] = json.dumps(sets["raw"], ensure_ascii=False, default=str)
    assignments = ", ".join(f"{k} = %s" for k in sets)
    await _query(f"UPDATE payments SET {assignments}, updated_at = NOW() "
                 f"WHERE provider = %s AND provider_payment_id = %s",
                 (*sets.values(), provider, provider_payment_id), table="payments")


async def list_payments(limit: int = 50, status: str = "") -> list:
    if status:
        return await _query("SELECT * FROM payments WHERE status = %s "
                            "ORDER BY created_at DESC LIMIT %s", (status, limit),
                            fetchall=True, table="payments") or []
    return await _query("SELECT * FROM payments ORDER BY created_at DESC LIMIT %s",
                        (limit,), fetchall=True, table="payments") or []


async def mark_event_seen(provider: str, event_id: str, event_type: str = "") -> bool:
    """True when this is the first time the event is seen.

    Webhook providers retry, so applying an event twice would double-credit a
    payment. The primary key on (provider, event_id) makes that impossible.

    This cannot go through ``_query``: ``INSERT ... ON CONFLICT DO NOTHING
    RETURNING`` yields no row both when the event is a duplicate and when the
    write failed, and those need opposite answers. So the success of the query
    itself is what is inspected here.

    When the table is missing the call fails OPEN (treated as new). Without the
    table there is no way to tell a retry from a first delivery, and re-applying
    is harmless because granting a plan is idempotent - whereas dropping the
    first real payment would silently take a customer's money.
    """
    if not provider or not event_id:
        return True
    if unavailable("billing_events"):
        return True
    try:
        row = await db.execute(
            "INSERT INTO billing_events (provider, event_id, event_type) "
            "VALUES (%s, %s, %s) ON CONFLICT (provider, event_id) DO NOTHING RETURNING event_id",
            (provider, event_id, event_type), fetchone=True)
    except Exception as exc:  # noqa: BLE001
        text = str(exc).lower()
        if any(marker in text for marker in _MISSING_MARKERS):
            _missing.add("billing_events")
        log.warning("billing: could not record event %s/%s (%s); applying anyway",
                    provider, event_id, type(exc).__name__)
        return True
    return row is not None


# --------------------------------------------------------------- admin

async def audit(admin_id: str, action: str, target_user_id: str = "", detail=None) -> None:
    await _query("INSERT INTO admin_audit (id, admin_id, action, target_user_id, detail) "
                 "VALUES (%s, %s, %s, %s, %s)",
                 (new_id(), admin_id, action, target_user_id or None,
                  json.dumps(detail or {}, ensure_ascii=False, default=str)),
                 table="admin_audit")


async def recent_audit(limit: int = 30) -> list:
    return await _query("SELECT * FROM admin_audit ORDER BY created_at DESC LIMIT %s",
                        (limit,), fetchall=True, table="admin_audit") or []


async def overview() -> dict:
    """Headline numbers for the admin dashboard."""
    users = await _query("SELECT COUNT(*) AS total, "
                         "COUNT(*) FILTER (WHERE created_at >= NOW() - INTERVAL '7 days') AS new_7d "
                         "FROM users", fetchone=True) or {}
    projects = await _query("SELECT COUNT(*) AS total, "
                            "COUNT(*) FILTER (WHERE render->>'status' = 'done') AS rendered "
                            "FROM projects", fetchone=True) or {}
    subs = await _query("SELECT plan, COUNT(*) AS n FROM subscriptions "
                        "WHERE status = 'active' GROUP BY plan", fetchall=True,
                        table="subscriptions") or []
    paid = await _query("SELECT COALESCE(SUM(amount), 0) AS amount, COUNT(*) AS n FROM payments "
                        "WHERE status = 'paid'", fetchone=True, table="payments") or {}
    return {
        "users": int(users.get("total") or 0),
        "new_users_7d": int(users.get("new_7d") or 0),
        "projects": int(projects.get("total") or 0),
        "videos_rendered": int(projects.get("rendered") or 0),
        "plans": {row.get("plan"): int(row.get("n") or 0) for row in subs if isinstance(row, dict)},
        "paid_count": int(paid.get("n") or 0),
        "paid_amount_minor": int(paid.get("amount") or 0),
        "billing_tables_ready": not any(unavailable(t) for t in
                                        ("subscriptions", "render_usage", "payments")),
        "generated_at": now_iso(),
    }


async def list_users(search: str = "", plan: str = "", limit: int = 25, offset: int = 0) -> list:
    """Users with their effective plan, for the admin table."""
    where, params = [], []
    if search:
        where.append("(LOWER(u.email) LIKE %s OR LOWER(u.name) LIKE %s)")
        like = f"%{search.lower()}%"
        params += [like, like]
    if plan:
        where.append("COALESCE(s.plan, u.plan, 'free') = %s")
        params.append(plan)
    clause = ("WHERE " + " AND ".join(where)) if where else ""
    rows = await _query(
        f"SELECT u.id, u.email, u.name, u.role, COALESCE(s.plan, u.plan, 'free') AS plan, "
        f"COALESCE(s.status, 'active') AS status, s.current_period_end, s.provider, "
        f"u.created_at, "
        f"(SELECT COUNT(*) FROM projects p WHERE p.user_id = u.id) AS projects, "
        f"(SELECT COUNT(*) FROM projects p WHERE p.user_id = u.id AND p.render->>'status' = 'done') AS rendered "
        f"FROM users u LEFT JOIN subscriptions s ON s.user_id = u.id "
        f"{clause} ORDER BY u.created_at DESC LIMIT %s OFFSET %s",
        (*params, limit, offset), fetchall=True)
    return rows or []


async def set_user_plan(user_id: str, plan: str, status: str = "active",
                        provider: str = "manual", interval: str = "month") -> bool:
    """Used by the admin dashboard to comp or correct an account."""
    saved = await upsert_subscription(user_id, plan=plan, status=status,
                                      provider=provider, interval=interval)
    # users.plan is the pre-billing source of truth, so keep it in step.
    await _query("UPDATE users SET plan = %s WHERE id = %s", (plan, user_id))
    return saved
