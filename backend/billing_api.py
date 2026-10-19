"""HTTP surface for pricing, checkout, webhooks and the admin dashboard.

Public:
    GET  /api/billing/plans          pricing in the visitor's currency
    POST /api/billing/webhook/razorpay
    POST /api/billing/webhook/dodo

Signed in:
    GET  /api/billing/me             plan, quota used, what resets when
    POST /api/billing/checkout       start a purchase

Administrators:
    GET  /api/admin/overview
    GET  /api/admin/users
    GET  /api/admin/payments
    GET  /api/admin/audit
    POST /api/admin/users/{user_id}/plan
"""
from __future__ import annotations

import calendar
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

import billing
import billing_store
import entitlements
import payments
from core import current_user, log
from admin_auth import require_admin  # isolated admin cookie, not users.role

router = APIRouter(prefix="/api/billing")
admin_router = APIRouter(prefix="/api/admin")

# Kept importable from here for existing callers/tests: the administrator
# dependency now lives in admin_auth, where the separate credential store is.
__all__ = ["router", "admin_router", "require_admin"]


# Country headers set by a platform edge. These are derived from the visitor's
# IP, so the browser cannot forge them.
EDGE_COUNTRY_HEADERS = ("cf-ipcountry", "x-vercel-ip-country", "x-country", "x-geo-country")

# "XX" means the edge could not determine a country, "T1" is a Tor exit node.
# Neither is a real country and both must fall through to the next signal.
UNKNOWN_COUNTRIES = {"", "XX", "T1"}


def _edge_country(request: Request) -> str:
    for header in EDGE_COUNTRY_HEADERS:
        value = (request.headers.get(header) or "").strip()
        if value.upper() not in UNKNOWN_COUNTRIES:
            return value
    return ""


def resolve_currency(request: Request, requested: str = "", country_hint: str = "") -> str:
    """Pick the billing currency, strongest signal first.

    1. Edge country header. Real IP geography and not spoofable, so when it is
       present it is final: an Indian visitor sees INR, everyone else USD.
       This is also what stops someone outside India claiming rupee pricing.
    2. Explicit ?currency=, for a deliberate link or a future currency switch.
    3. country_hint from the browser timezone. A host without an edge country
       header (local development, or an API served directly) has no signal at
       all, which would show USD to an Indian visitor. The browser is the
       fallback so that case still resolves correctly.
    4. USD.
    """
    edge = _edge_country(request)
    if edge:
        return billing.currency_for_country(edge)
    explicit = (requested or "").strip().upper()
    if explicit in billing.CURRENCY_SYMBOL:
        return explicit
    if country_hint:
        return billing.currency_for_country(country_hint)
    return billing.currency_for_country(None)


def currency_source(request: Request, requested: str = "", country_hint: str = "") -> str:
    """Which signal decided the currency. Exposed for debugging a live deploy."""
    if _edge_country(request):
        return "edge"
    if (requested or "").strip().upper() in billing.CURRENCY_SYMBOL:
        return "requested"
    if country_hint:
        return "browser_hint"
    return "default"


# ------------------------------------------------------------------ public

@router.get("/plans")
async def plans(request: Request, currency: Optional[str] = None, country: str = ""):
    chosen = resolve_currency(request, currency or "", country)
    return {
        "currency": chosen,
        # Lets an operator confirm on a live deploy that edge geography is
        # actually arriving, rather than silently defaulting every visitor.
        "currency_source": currency_source(request, currency or "", country),
        "annual_discount_percent": int(round(billing.annual_discount() * 100)),
        "provider": billing.provider_for(chosen),
        "checkout_live": billing.provider_configured(chosen),
        "plans": billing.public_plans(chosen),
    }


# ------------------------------------------------------------------ signed in

@router.get("/me")
async def me(user: dict = Depends(current_user)):
    ent = await entitlements.entitlement(user)
    ent["checkout_live"] = billing.provider_configured(ent["currency"])
    return ent


class CheckoutIn(BaseModel):
    plan: str = Field(min_length=1)
    interval: str = "month"
    currency: Optional[str] = None
    country: Optional[str] = None
    return_url: Optional[str] = None


@router.post("/checkout")
async def checkout(body: CheckoutIn, request: Request, user: dict = Depends(current_user)):
    # Same resolver the pricing page used, so the amount charged is the amount
    # displayed. Edge geography still outranks anything the browser sends.
    currency = resolve_currency(request, body.currency or "", body.country or "")
    return await payments.create_checkout(user, body.plan, body.interval, currency,
                                          body.return_url or "")


# ------------------------------------------------------------------ webhooks

def _add_months(moment: datetime, months: int) -> datetime:
    month = moment.month - 1 + months
    year = moment.year + month // 12
    month = month % 12 + 1
    day = min(moment.day, calendar.monthrange(year, month)[1])
    return moment.replace(year=year, month=month, day=day)


def _period_end(interval: str) -> str:
    now = datetime.now(timezone.utc)
    end = _add_months(now, 12) if interval == "year" else _add_months(now, 1)
    return end.isoformat()


@router.post("/webhook/razorpay")
async def razorpay_webhook(request: Request):
    body = await request.body()
    if not payments.verify_razorpay(body, request.headers.get("x-razorpay-signature", "")):
        # A signature we cannot verify is never trusted. This is the only
        # correct answer to an unsigned or mis-signed delivery.
        raise HTTPException(400, "Invalid webhook signature")
    try:
        event = await request.json()
    except Exception:  # noqa: BLE001
        raise HTTPException(400, "Malformed webhook payload")

    event_type = event.get("event", "")
    entity = ((event.get("payload") or {}).get("payment") or {}).get("entity") or {}
    event_id = (request.headers.get("x-razorpay-event-id")
                or f"{event_type}:{entity.get('id', '')}")
    if not event_id:
        raise HTTPException(400, "Webhook has no event id")

    notes = entity.get("notes") or {}
    user_id = notes.get("user_id", "")
    plan_id = notes.get("plan", "")
    interval = "year" if notes.get("interval") == "year" else "month"

    if event_type in ("payment.captured", "order.paid", "payment.authorized"):
        if not plan_id or billing.plan(plan_id).get("tier", 0) <= 0:
            log.warning("billing: razorpay payment without a paid plan in notes (event %s)", event_id)
            return {"ok": True, "applied": False, "reason": "no plan in notes"}
        result = await payments.apply_paid_event(
            "razorpay", event_id, event_type, user_id, plan_id, interval,
            entity.get("currency", "INR"), int(entity.get("amount") or 0),
            provider_payment_id=entity.get("id", ""), email=entity.get("email", ""),
            period_end=_period_end(interval), raw=entity)
        return {"ok": True, **result}

    if event_type in ("payment.failed",):
        await billing_store.mark_event_seen("razorpay", event_id, event_type)
        await billing_store.update_payment_by_provider_id(
            "razorpay", entity.get("order_id", ""), status="failed", raw=entity)
        return {"ok": True, "applied": False, "reason": "payment failed"}

    await billing_store.mark_event_seen("razorpay", event_id, event_type)
    return {"ok": True, "applied": False, "reason": f"ignored {event_type}"}


@router.post("/webhook/dodo")
async def dodo_webhook(request: Request):
    body = await request.body()
    if not payments.verify_dodo(request.headers, body):
        raise HTTPException(400, "Invalid webhook signature")
    try:
        event = await request.json()
    except Exception:  # noqa: BLE001
        raise HTTPException(400, "Malformed webhook payload")

    event_type = event.get("type", "")
    data = event.get("data") or {}
    event_id = request.headers.get("webhook-id") or f"{event_type}:{data.get('payment_id', '')}"
    metadata = data.get("metadata") or {}
    user_id = metadata.get("user_id", "")
    plan_id = metadata.get("plan", "")
    interval = "year" if metadata.get("interval") == "year" else "month"
    email = (data.get("customer") or {}).get("email", "")

    if event_type in ("payment.succeeded", "payment.completed", "subscription.active"):
        if not plan_id or billing.plan(plan_id).get("tier", 0) <= 0:
            log.warning("billing: dodo payment without a paid plan in metadata (event %s)", event_id)
            return {"ok": True, "applied": False, "reason": "no plan in metadata"}
        result = await payments.apply_paid_event(
            "dodo", event_id, event_type, user_id, plan_id, interval,
            data.get("currency", "USD"), int(data.get("total_amount") or data.get("amount") or 0),
            provider_payment_id=data.get("payment_id", ""),
            provider_subscription_id=data.get("subscription_id", ""),
            email=email, period_end=_period_end(interval), raw=data)
        return {"ok": True, **result}

    if event_type in ("subscription.cancelled", "subscription.expired", "payment.failed"):
        result = await payments.apply_cancellation(
            "dodo", event_id, event_type, data.get("subscription_id", ""), user_id)
        return {"ok": True, **result}

    await billing_store.mark_event_seen("dodo", event_id, event_type)
    return {"ok": True, "applied": False, "reason": f"ignored {event_type}"}


# ------------------------------------------------------------------ admin

@admin_router.get("/overview")
async def admin_overview(_: dict = Depends(require_admin)):
    return await billing_store.overview()


@admin_router.get("/users")
async def admin_users(search: str = "", plan: str = "", limit: int = 25, offset: int = 0,
                      _: dict = Depends(require_admin)):
    limit = max(1, min(limit, 200))
    return {"users": await billing_store.list_users(search, plan, limit, offset),
            "limit": limit, "offset": offset}


@admin_router.get("/payments")
async def admin_payments(status: str = "", limit: int = 50, _: dict = Depends(require_admin)):
    limit = max(1, min(limit, 200))
    return {"payments": await billing_store.list_payments(limit, status)}


@admin_router.get("/audit")
async def admin_audit(limit: int = 30, _: dict = Depends(require_admin)):
    return {"audit": await billing_store.recent_audit(max(1, min(limit, 200)))}


class PlanChangeIn(BaseModel):
    plan: str = Field(min_length=1)
    status: str = "active"


@admin_router.post("/users/{user_id}/plan")
async def admin_set_plan(user_id: str, body: PlanChangeIn, admin: dict = Depends(require_admin)):
    if body.plan not in billing.catalog():
        raise HTTPException(400, f"Unknown plan '{body.plan}'")
    saved = await billing_store.set_user_plan(user_id, body.plan, body.status)
    await billing_store.audit(admin.get("id", ""), "set_plan", user_id,
                              {"plan": body.plan, "status": body.status, "persisted": saved})
    return {"ok": True, "persisted": saved, "plan": body.plan}
