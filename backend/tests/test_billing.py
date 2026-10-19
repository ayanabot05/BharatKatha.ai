"""Billing, entitlement and webhook verification tests.

The database is faked at the same seam the app uses (``billing_store.db``), so
these tests exercise the real query shapes, the real fail-soft behaviour and the
real signature checks without a live Postgres.
"""
import asyncio
import base64
import functools
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone

import pytest

import billing
import billing_store
import entitlements
import payments


def async_test(fn):
    """Run an async test without adding pytest-asyncio to the project."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        return asyncio.run(fn(*args, **kwargs))
    return wrapper


class FakeDB:
    """Routes the handful of queries billing issues, by substring."""

    def __init__(self, rendered=0, subscription=None, used=None, missing=()):
        self.rendered = rendered
        self.subscription = subscription
        self.used = used
        self.missing = set(missing)
        self.queries = []

    async def execute(self, query, params=(), fetchone=False, fetchall=False, commit=True):
        q = " ".join(str(query).split()).lower()
        self.queries.append(q)
        for table in self.missing:
            if table in q:
                raise RuntimeError(f'relation "{table}" does not exist')
        if "render_usage" in q:
            return {"used": self.used} if self.used is not None else None
        if "from subscriptions" in q:
            return self.subscription
        if "from projects" in q and "count(*)" in q:
            return {"n": self.rendered}
        if "billing_events" in q:
            # First insert wins; a repeat conflicts and returns nothing.
            if getattr(self, "_seen", None) == (params[0], params[1]):
                return None
            self._seen = (params[0], params[1])
            return {"event_id": params[1]}
        if "insert into render_usage" in q:
            self.used = (self.used or 0) + 1
            return {"used": self.used}
        return None if fetchone else []


@pytest.fixture(autouse=True)
def clean_state(monkeypatch):
    """Each test starts with no cached catalog and no remembered missing tables."""
    monkeypatch.setattr(billing, "_catalog_cache", None)
    monkeypatch.setattr(billing_store, "_missing", set())
    for key in ("BILLING_PLANS_JSON", "BILLING_ANNUAL_DISCOUNT", "RAZORPAY_WEBHOOK_SECRET",
                "DODO_WEBHOOK_SECRET", "RAZORPAY_KEY_ID", "RAZORPAY_KEY_SECRET",
                "DODO_API_KEY", "BILLING_FREE_VIDEOS", "BILLING_FREE_PERIOD"):
        monkeypatch.delenv(key, raising=False)
    yield


def use_db(monkeypatch, **kwargs):
    fake = FakeDB(**kwargs)
    monkeypatch.setattr(billing_store, "db", fake)
    return fake


# ------------------------------------------------------------------ plan maths

def test_free_tier_is_two_videos_per_month():
    videos, period, max_seconds = billing.quota_for("free")
    assert (videos, period, max_seconds) == (2, "month", 30)


def test_paid_tiers_are_explicit_not_defaulted():
    assert billing.quota_for("creator")[:2] == (8, "month")
    assert billing.quota_for("studio")[:2] == (16, "month")


def test_annual_price_is_fifteen_percent_off_twelve_months():
    for currency in ("INR", "USD"):
        for plan in billing.public_plans(currency):
            if plan["tier"] == 0:
                continue
            assert plan["savings_percent"] == 15
            full = plan["month"] * 12
            assert plan["year"] < full
            assert abs(plan["year"] - full * 0.85) <= 60  # whole-rupee rounding


def test_inr_annual_prices_are_whole_rupees():
    for plan in billing.public_plans("INR"):
        if plan["tier"] > 0:
            assert plan["year"] % 100 == 0, "paise must not appear in an INR annual price"


def test_published_prices_and_the_length_ladder():
    """Pin the live catalogue. Free 30 s, Creator 60 s, Studio 75 s.

    75 s is kept on the top tier on purpose: it is a marketed length, so if no
    plan allows it the studio preset would 402 for every customer.
    """
    inr = {plan["id"]: plan for plan in billing.public_plans("INR")}
    usd = {plan["id"]: plan for plan in billing.public_plans("USD")}
    assert inr["creator"]["month_display"] == "\u20b9549"
    assert inr["studio"]["month_display"] == "\u20b91,299"
    assert usd["creator"]["month_display"] == "$8.99"
    assert usd["studio"]["month_display"] == "$19.99"
    assert (inr["free"]["videos"], inr["creator"]["videos"],
            inr["studio"]["videos"]) == (2, 8, 16)
    assert (inr["free"]["max_seconds"], inr["creator"]["max_seconds"],
            inr["studio"]["max_seconds"]) == (30, 60, 75)


def test_india_is_inr_everything_else_usd():
    assert billing.currency_for_country("IN") == "INR"
    assert billing.currency_for_country("in") == "INR"
    assert billing.currency_for_country("US") == "USD"
    assert billing.currency_for_country(None) == "USD"


def test_prices_are_configurable(monkeypatch):
    override = {"pro": {"id": "pro", "name": "Pro", "tier": 1,
                        "prices": {"INR": {"month": 100, "year": 1020},
                                   "USD": {"month": 2, "year": 21}},
                        "quota": {"videos": 5, "period": "month"}, "max_seconds": 30}}
    monkeypatch.setenv("BILLING_PLANS_JSON", json.dumps(override))
    assert billing.plan("pro")["name"] == "Pro"
    assert billing.quota_for("pro")[0] == 5
    assert billing.public_plans("INR")[0]["month_display"] == "\u20b91"


def test_a_broken_override_falls_back_instead_of_crashing(monkeypatch):
    monkeypatch.setenv("BILLING_PLANS_JSON", "{not json")
    assert billing.catalog()["free"]["id"] == "free"


def test_checkout_provider_is_razorpay_for_inr_and_dodo_for_usd():
    assert billing.provider_for("INR") == "razorpay"
    assert billing.provider_for("USD") == "dodo"


def test_checkout_is_not_live_without_credentials(monkeypatch):
    assert billing.provider_configured("INR") is False
    monkeypatch.setenv("RAZORPAY_KEY_ID", "rzp_test_x")
    monkeypatch.setenv("RAZORPAY_KEY_SECRET", "secret")
    assert billing.provider_configured("INR") is True


# ------------------------------------------------------------------ windows

def test_week_window_starts_on_monday_and_key_is_iso_week():
    wednesday = datetime(2026, 10, 14, 12, tzinfo=timezone.utc)
    start = billing.period_start("week", wednesday)
    assert start.weekday() == 0
    assert start.date().isoformat() == "2026-10-12"
    assert billing.period_key("week", wednesday) == "2026-W42"


def test_reset_date_is_after_now_for_every_period():
    now = datetime.now(timezone.utc)
    for period in ("day", "week", "month"):
        assert datetime.fromisoformat(billing.period_reset(period, now)) > now


# ------------------------------------------------------------------ entitlement

@async_test
async def test_free_user_gets_a_real_allowance_then_is_blocked(monkeypatch):
    use_db(monkeypatch, rendered=1)
    allowed, _, ent = await entitlements.can_render({"id": "u1", "plan": "free"}, 30)
    assert allowed is True
    assert (ent["videos_allowed"], ent["videos_used"], ent["videos_remaining"]) == (2, 1, 1)

    use_db(monkeypatch, rendered=2)
    allowed, reason, ent = await entitlements.can_render({"id": "u1", "plan": "free"}, 30)
    assert allowed is False
    assert "used all 2 videos" in reason
    assert ent["resets_at"][:4].isdigit(), "the creator is told when it resets"


@async_test
async def test_free_plan_blocks_a_length_only_a_paid_plan_allows(monkeypatch):
    use_db(monkeypatch, rendered=0)
    allowed, reason, _ = await entitlements.can_render({"id": "u1", "plan": "free"}, 75)
    assert allowed is False
    assert "up to 30 seconds" in reason


@async_test
async def test_paid_plan_raises_both_the_cap_and_the_length(monkeypatch):
    use_db(monkeypatch, rendered=7,
           subscription={"user_id": "u1", "plan": "creator", "status": "active",
                         "currency": "INR", "interval": "month", "current_period_end": None})
    allowed, _, ent = await entitlements.can_render({"id": "u1"}, 60)
    assert allowed is True
    assert (ent["videos_allowed"], ent["max_seconds"]) == (8, 60)


@async_test
async def test_only_the_top_tier_reaches_the_longest_length(monkeypatch):
    """75 s is a Studio feature; Creator stops at 60 s and Free at 30 s."""
    use_db(monkeypatch, rendered=0,
           subscription={"user_id": "u1", "plan": "studio", "status": "active",
                         "currency": "INR", "interval": "month", "current_period_end": None})
    allowed, _, ent = await entitlements.can_render({"id": "u1"}, 75)
    assert allowed is True
    assert (ent["videos_allowed"], ent["max_seconds"]) == (16, 75)

    use_db(monkeypatch, rendered=0,
           subscription={"user_id": "u1", "plan": "creator", "status": "active",
                         "currency": "INR", "interval": "month", "current_period_end": None})
    blocked, reason, _ = await entitlements.can_render({"id": "u1"}, 75)
    assert blocked is False
    assert "up to 60 seconds" in reason


@async_test
async def test_expired_paid_plan_drops_back_to_free(monkeypatch):
    past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    use_db(monkeypatch, rendered=0,
           subscription={"user_id": "u1", "plan": "creator", "status": "active",
                         "current_period_end": past, "currency": "USD"})
    ent = await entitlements.entitlement({"id": "u1"})
    assert ent["plan"] == "free"
    assert ent["videos_allowed"] == 2
    assert ent["max_seconds"] == 30


@async_test
async def test_cancelled_plan_keeps_access_until_the_period_ends(monkeypatch):
    future = (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()
    use_db(monkeypatch, rendered=0,
           subscription={"user_id": "u1", "plan": "studio", "status": "cancelled",
                         "current_period_end": future, "currency": "INR"})
    ent = await entitlements.entitlement({"id": "u1"})
    assert ent["plan"] == "studio"
    assert ent["status"] == "cancelled"
    assert ent["videos_allowed"] == 16


@async_test
async def test_quota_still_works_when_billing_tables_are_missing(monkeypatch):
    """The free allowance must be enforceable before any migration is applied."""
    use_db(monkeypatch, rendered=2, missing=("subscriptions", "render_usage"))
    allowed, reason, ent = await entitlements.can_render({"id": "u1", "plan": "free"}, 30)
    assert allowed is False
    assert "used all 2 videos" in reason
    assert billing_store.unavailable("subscriptions") is True


@async_test
async def test_counter_table_is_preferred_over_the_project_count(monkeypatch):
    use_db(monkeypatch, rendered=0, used=2)
    ent = await entitlements.entitlement({"id": "u1", "plan": "free"})
    assert ent["videos_used"] == 2


# ------------------------------------------------------------------ signatures

def test_razorpay_signature_is_required_and_checked(monkeypatch):
    monkeypatch.setenv("RAZORPAY_WEBHOOK_SECRET", "whsec_rzp")
    body = json.dumps({"event": "payment.captured"}).encode()
    good = hmac.new(b"whsec_rzp", body, hashlib.sha256).hexdigest()
    assert payments.verify_razorpay(body, good) is True
    assert payments.verify_razorpay(body, "deadbeef") is False
    assert payments.verify_razorpay(body, "") is False
    assert payments.verify_razorpay(body + b" ", good) is False


def test_razorpay_signature_rejected_when_secret_is_unset():
    assert payments.verify_razorpay(b"{}", "anything") is False


def _dodo_headers(secret, body, msg_id="msg_1", ts="1700000000", tamper=False):
    key = base64.b64decode(secret[len("whsec_"):])
    signed = f"{msg_id}.{ts}.".encode() + (body + b"x" if tamper else body)
    sig = base64.b64encode(hmac.new(key, signed, hashlib.sha256).digest()).decode()
    return {"webhook-id": msg_id, "webhook-timestamp": ts, "webhook-signature": f"v1,{sig}"}


def test_dodo_webhook_uses_the_svix_scheme(monkeypatch):
    secret = "whsec_" + base64.b64encode(b"a-strong-test-secret-value").decode()
    monkeypatch.setenv("DODO_WEBHOOK_SECRET", secret)
    body = json.dumps({"type": "payment.succeeded"}).encode()
    assert payments.verify_dodo(_dodo_headers(secret, body), body) is True
    assert payments.verify_dodo(_dodo_headers(secret, body, tamper=True), body) is False
    assert payments.verify_dodo({}, body) is False
    assert payments.verify_dodo({"webhook-id": "m", "webhook-timestamp": "1",
                                 "webhook-signature": "v1,zzz"}, body) is False


# ------------------------------------------------------------------ webhooks

@async_test
async def test_a_repeated_webhook_is_not_applied_twice(monkeypatch):
    fake = use_db(monkeypatch)
    first = await billing_store.mark_event_seen("razorpay", "evt_1", "payment.captured")
    second = await billing_store.mark_event_seen("razorpay", "evt_1", "payment.captured")
    assert first is True
    assert second is False, "a retried delivery must not double-credit a payment"


@async_test
async def test_paid_event_grants_the_plan_and_records_the_payment(monkeypatch):
    fake = use_db(monkeypatch)
    result = await payments.apply_paid_event(
        "razorpay", "evt_9", "payment.captured", "u1", "creator", "year", "INR",
        299900, provider_payment_id="pay_9", email="a@b.com",
        period_end="2027-01-01T00:00:00+00:00", raw={"ok": True})
    assert result["applied"] is True
    assert any("insert into subscriptions" in q for q in fake.queries)
    assert any("insert into payments" in q for q in fake.queries)


@async_test
async def test_paid_event_without_a_user_is_refused(monkeypatch):
    use_db(monkeypatch)
    result = await payments.apply_paid_event(
        "dodo", "evt_10", "payment.succeeded", "", "creator", "month", "USD", 499)
    assert result["applied"] is False
    assert result["reason"] == "missing user"


@async_test
async def test_checkout_reports_honestly_when_not_configured(monkeypatch):
    use_db(monkeypatch)
    out = await payments.create_checkout({"id": "u1", "email": "a@b.com"}, "creator", "month", "INR")
    assert out["ready"] is False
    assert "switched on" in out["reason"]
    assert out["provider"] == "razorpay"


@async_test
async def test_free_plan_never_reaches_checkout(monkeypatch):
    use_db(monkeypatch)
    out = await payments.create_checkout({"id": "u1"}, "free", "month", "USD")
    assert out["ready"] is False
    assert "does not need checkout" in out["reason"]


# ------------------------------------------------------------------ good errors

@async_test
async def test_every_blocked_reason_is_a_sentence_a_creator_can_act_on(monkeypatch):
    use_db(monkeypatch, rendered=2)
    _, reason, _ = await entitlements.can_render({"id": "u1", "plan": "free"}, 30)
    assert reason.endswith(".")
    assert "Upgrade" in reason

    use_db(monkeypatch, rendered=0)
    _, reason, _ = await entitlements.can_render({"id": "u1", "plan": "free"}, 60)
    assert reason.endswith(".")
    assert "Upgrade" in reason
