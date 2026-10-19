"""Checkout creation and webhook verification for Razorpay (INR) and Dodo (USD).

Nothing here runs until credentials exist. ``billing.provider_configured`` is the
single gate, so the product can ship today with the pricing visible and checkout
switched off, then go live by setting environment variables.

Environment
    Razorpay (INR)
        RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET, RAZORPAY_WEBHOOK_SECRET
    Dodo Payments (USD)
        DODO_API_KEY, DODO_WEBHOOK_SECRET
        DODO_PRODUCT_IDS_JSON   {"creator":{"month":"pdt_..","year":"pdt_.."}, ...}
        DODO_API_BASE           default https://live.dodopayments.com
    RAZORPAY_API_BASE           default https://api.razorpay.com

Webhooks are verified by signature. An unsigned or mis-signed delivery is
rejected - never trusted - and every accepted event is recorded once.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os

import httpx

import billing
import billing_store
from core import log, new_id

TIMEOUT = httpx.Timeout(20.0, connect=10.0)

RAZORPAY_BASE = os.environ.get("RAZORPAY_API_BASE", "https://api.razorpay.com").rstrip("/")
DODO_BASE = os.environ.get("DODO_API_BASE", "https://live.dodopayments.com").rstrip("/")


def configured(currency: str) -> bool:
    return billing.provider_configured(currency)


def _env(name: str) -> str:
    return os.environ.get(name, "").strip()


def _amount_for(plan_id: str, interval: str, currency: str) -> int:
    prices = (billing.plan(plan_id).get("prices") or {}).get(currency.upper()) or {}
    return int(prices.get("year" if interval == "year" else "month") or 0)


def _dodo_product_id(plan_id: str, interval: str) -> str:
    raw = _env("DODO_PRODUCT_IDS_JSON")
    if not raw:
        return ""
    try:
        table = json.loads(raw)
    except json.JSONDecodeError:
        return ""
    if not isinstance(table, dict):
        return ""
    per_plan = table.get(plan_id) or {}
    if isinstance(per_plan, str):
        return per_plan
    if isinstance(per_plan, dict):
        return str(per_plan.get(interval) or per_plan.get("month") or "")
    return ""


async def create_checkout(user: dict, plan_id: str, interval: str, currency: str,
                          return_url: str = "") -> dict:
    """Create a checkout session. Returns a dict the UI can act on.

    Never raises for a configuration gap: it returns ``ready: False`` with a
    plain-language reason, which the pricing page shows instead of a dead button.
    """
    currency = (currency or "USD").upper()
    interval = "year" if interval == "year" else "month"
    plan = billing.plan(plan_id)
    if plan.get("tier", 0) <= 0:
        return {"ready": False, "reason": "The Free plan does not need checkout.",
                "provider": "", "currency": currency, "amount": 0}

    provider = billing.provider_for(currency)
    if not provider:
        return {"ready": False, "currency": currency, "amount": 0, "provider": "",
                "reason": f"No payment provider is configured for {currency}."}
    if not configured(currency):
        return {"ready": False, "provider": provider, "currency": currency, "amount": 0,
                "reason": "Card and UPI checkout is being switched on. "
                          "Please try again shortly, or contact us to start now."}

    amount = _amount_for(plan_id, interval, currency)
    if amount <= 0:
        return {"ready": False, "provider": provider, "currency": currency, "amount": 0,
                "reason": "This plan is not priced in this currency."}

    notes = {"user_id": user.get("id", ""), "plan": plan_id, "interval": interval,
             "email": user.get("email", "")}

    if provider == "razorpay":
        return await _razorpay_order(plan_id, interval, amount, currency, notes)
    return await _dodo_payment(plan_id, interval, amount, currency, notes, user, return_url)


async def _razorpay_order(plan_id, interval, amount, currency, notes) -> dict:
    payload = {"amount": amount, "currency": currency, "receipt": new_id()[:40], "notes": notes}
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(f"{RAZORPAY_BASE}/v1/orders", json=payload,
                                     auth=(_env("RAZORPAY_KEY_ID"), _env("RAZORPAY_KEY_SECRET")))
            resp.raise_for_status()
            order = resp.json()
    except httpx.HTTPStatusError as exc:
        log.warning("razorpay order failed: %s %s", exc.response.status_code, exc.response.text[:300])
        return {"ready": False, "provider": "razorpay", "currency": currency, "amount": amount,
                "reason": "The payment gateway rejected the request. Please try again."}
    except Exception as exc:  # noqa: BLE001
        log.warning("razorpay order error: %s: %s", type(exc).__name__, exc)
        return {"ready": False, "provider": "razorpay", "currency": currency, "amount": amount,
                "reason": "Could not reach the payment gateway. Please try again."}

    order_id = order.get("id", "")
    await billing_store.record_payment(
        user_id=notes.get("user_id"), email=notes.get("email"), provider="razorpay",
        provider_order_id=order_id, plan=plan_id, interval=interval, currency=currency,
        amount=amount, status="created", raw=order)

    return {"ready": True, "provider": "razorpay", "currency": currency, "amount": amount,
            "order_id": order_id, "key_id": _env("RAZORPAY_KEY_ID"),
            "plan": plan_id, "interval": interval, "email": notes.get("email"),
            "description": f"BharatChitra AI {billing.plan(plan_id).get('name', plan_id)} "
                           f"({interval}ly)"}


async def _dodo_payment(plan_id, interval, amount, currency, notes, user, return_url) -> dict:
    product_id = _dodo_product_id(plan_id, interval)
    if not product_id:
        return {"ready": False, "provider": "dodo", "currency": currency, "amount": amount,
                "reason": "This plan is not linked to a payment product yet."}
    payload = {
        "payment_link": True,
        "product_cart": [{"product_id": product_id, "quantity": 1}],
        "customer": {"email": user.get("email", ""), "name": user.get("name", "")},
        "metadata": notes,
    }
    if return_url:
        payload["return_url"] = return_url
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(f"{DODO_BASE}/payments", json=payload,
                                     headers={"Authorization": f"Bearer {_env('DODO_API_KEY')}"})
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as exc:
        log.warning("dodo payment failed: %s %s", exc.response.status_code, exc.response.text[:300])
        return {"ready": False, "provider": "dodo", "currency": currency, "amount": amount,
                "reason": "The payment gateway rejected the request. Please try again."}
    except Exception as exc:  # noqa: BLE001
        log.warning("dodo payment error: %s: %s", type(exc).__name__, exc)
        return {"ready": False, "provider": "dodo", "currency": currency, "amount": amount,
                "reason": "Could not reach the payment gateway. Please try again."}

    url = data.get("payment_link") or data.get("checkout_url") or ""
    await billing_store.record_payment(
        user_id=notes.get("user_id"), email=notes.get("email"), provider="dodo",
        provider_order_id=data.get("payment_id") or data.get("id") or "",
        plan=plan_id, interval=interval, currency=currency, amount=amount,
        status="created", raw=data)
    if not url:
        return {"ready": False, "provider": "dodo", "currency": currency, "amount": amount,
                "reason": "The gateway did not return a checkout link. Please try again."}
    return {"ready": True, "provider": "dodo", "currency": currency, "amount": amount,
            "url": url, "plan": plan_id, "interval": interval}


# ----------------------------------------------------------------- verification

def verify_razorpay(body: bytes, signature: str) -> bool:
    secret = _env("RAZORPAY_WEBHOOK_SECRET")
    if not secret or not signature:
        return False
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def verify_dodo(headers, body: bytes) -> bool:
    """Svix-style signature used by Dodo Payments.

    Signed content is ``{webhook-id}.{webhook-timestamp}.{body}``, HMAC-SHA256
    with the base64-decoded secret. The header may list several space-separated
    ``v1,<base64>`` candidates during a secret rotation.
    """
    secret = _env("DODO_WEBHOOK_SECRET")
    if not secret:
        return False
    msg_id = headers.get("webhook-id", "")
    timestamp = headers.get("webhook-timestamp", "")
    signatures = headers.get("webhook-signature", "")
    if not (msg_id and timestamp and signatures):
        return False
    key = secret[len("whsec_"):] if secret.startswith("whsec_") else secret
    try:
        key_bytes = base64.b64decode(key)
    except Exception:  # noqa: BLE001
        return False
    signed = f"{msg_id}.{timestamp}.".encode() + body
    expected = base64.b64encode(
        hmac.new(key_bytes, signed, hashlib.sha256).digest()).decode()
    for candidate in signatures.split():
        _, _, value = candidate.partition(",")
        if value and hmac.compare_digest(value, expected):
            return True
    return False


# ----------------------------------------------------------------- applying

async def apply_paid_event(provider: str, event_id: str, event_type: str,
                           user_id: str, plan_id: str, interval: str, currency: str,
                           amount: int, provider_payment_id: str = "",
                           provider_subscription_id: str = "", email: str = "",
                           period_end: str = "", raw=None) -> dict:
    """Grant entitlement for a verified payment, exactly once."""
    fresh = await billing_store.mark_event_seen(provider, event_id, event_type)
    if not fresh:
        return {"applied": False, "reason": "duplicate event"}

    if not user_id:
        log.warning("billing: %s event %s has no user_id; cannot grant entitlement",
                    provider, event_id)
        return {"applied": False, "reason": "missing user"}

    saved = await billing_store.upsert_subscription(
        user_id, plan=plan_id, status="active", provider=provider,
        currency=currency.upper(), interval=interval,
        provider_subscription_id=provider_subscription_id or None,
        current_period_end=period_end or None)
    await billing_store.set_user_plan(user_id, plan_id, status="active",
                                      provider=provider, interval=interval)
    await billing_store.record_payment(
        user_id=user_id, email=email, provider=provider,
        provider_payment_id=provider_payment_id or None, plan=plan_id,
        interval=interval, currency=currency.upper(), amount=amount,
        status="paid", raw=raw)
    log.info("billing: %s %s applied for user %s -> %s", provider, event_type, user_id, plan_id)
    return {"applied": True, "persisted": saved, "plan": plan_id}


async def apply_cancellation(provider: str, event_id: str, event_type: str,
                             provider_subscription_id: str, user_id: str = "") -> dict:
    fresh = await billing_store.mark_event_seen(provider, event_id, event_type)
    if not fresh:
        return {"applied": False, "reason": "duplicate event"}
    sub = await billing_store.get_subscription(user_id) if user_id else None
    if not sub and provider_subscription_id:
        sub = await _subscription_by_provider_id(provider, provider_subscription_id)
    if not sub:
        return {"applied": False, "reason": "no subscription"}
    # Access continues until the paid period ends; entitlement() enforces that.
    await billing_store.upsert_subscription(sub["user_id"], status="cancelled")
    return {"applied": True, "status": "cancelled"}


async def _subscription_by_provider_id(provider: str, provider_subscription_id: str):
    from billing_store import _query  # local import keeps the fail-soft helper private
    return await _query(
        "SELECT * FROM subscriptions WHERE provider = %s AND provider_subscription_id = %s LIMIT 1",
        (provider, provider_subscription_id), fetchone=True, table="subscriptions")
