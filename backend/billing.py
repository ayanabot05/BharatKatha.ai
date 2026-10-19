"""Plan catalog, pricing and entitlements.

This is the single source of truth for what a plan costs and what it allows.
Checkout, the landing page, quota enforcement and the admin dashboard all read
from here, so a price change happens in exactly one place.

Prices are stored in MINOR UNITS (paise for INR, cents for USD) as integers.
Never store money as a float - 4.99 as a float does not round-trip.

Everything can be overridden at runtime without a code change:

    BILLING_PLANS_JSON   full plan catalog (JSON)
    BILLING_ANNUAL_DISCOUNT   annual discount as a decimal, default 0.15
    BILLING_FREE_VIDEOS / BILLING_FREE_PERIOD   free tier allowance

Payment providers: Razorpay for INR, Dodo Payments for USD.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone

# ---------------------------------------------------------------- currency

# Countries billed in INR. Everything else is billed in USD.
INR_COUNTRIES = {"IN", "IND"}

# Providers must match what is actually integrated. Razorpay settles INR,
# Dodo settles USD; a currency with no provider is display-only.
PROVIDER_BY_CURRENCY = {"INR": "razorpay", "USD": "dodo"}

CURRENCY_SYMBOL = {"INR": "\u20b9", "USD": "$"}

# Minor units per major unit.
MINOR_UNITS = {"INR": 100, "USD": 100}


def currency_for_country(country: str | None) -> str:
    """INR inside India, USD everywhere else."""
    if country and str(country).strip().upper() in INR_COUNTRIES:
        return "INR"
    return "USD"


def provider_for(currency: str) -> str:
    return PROVIDER_BY_CURRENCY.get((currency or "").upper(), "")


# Credentials each provider needs before a live checkout can be created.
PROVIDER_ENV = {
    "razorpay": ("RAZORPAY_KEY_ID", "RAZORPAY_KEY_SECRET"),
    "dodo": ("DODO_API_KEY",),
}


def provider_configured(currency: str) -> bool:
    """True only when the provider for this currency has usable credentials.

    Gates the live checkout so the UI can honestly say whether buying works yet.
    """
    keys = PROVIDER_ENV.get(provider_for(currency))
    if not keys:
        return False
    return all(os.environ.get(key, "").strip() for key in keys)


def annual_discount() -> float:
    raw = os.environ.get("BILLING_ANNUAL_DISCOUNT", "0.15")
    try:
        value = float(raw)
    except ValueError:
        return 0.15
    return min(max(value, 0.0), 0.9)


# ---------------------------------------------------------------- catalog

def _price_pair(currency: str, month_minor: int, discount: float) -> dict:
    """Annual price derived from the monthly price.

    Rounded to a whole major unit for INR, so the annual price reads as
    Rs 3,049 rather than Rs 3,049.80. USD keeps the exact cent.
    """
    year = month_minor * 12 * (1.0 - discount)
    if currency == "INR":
        step = MINOR_UNITS.get("INR", 100)
        year = int(round(year / step) * step)
    else:
        year = int(round(year))
    return {"month": month_minor, "year": year}


def _default_catalog() -> dict:
    discount = annual_discount()
    free = {
        "id": "free",
        "name": "Free",
        "tagline": "Try the studio. No card needed.",
        "tier": 0,
        "prices": {"INR": {"month": 0, "year": 0}, "USD": {"month": 0, "year": 0}},
        "max_seconds": 30,
        "features": [
            "2 videos per month",
            "Videos up to 30 seconds",
            "All 11 Indian languages",
            "All 6 art styles",
            "Burned-in captions and SRT download",
            "BharatKatha watermark",
        ],
    }
    creator = {
        "id": "creator",
        "name": "Creator",
        "tagline": "For storytellers publishing every week.",
        "tier": 1,
        "popular": True,
        "prices": {
            "INR": _price_pair("INR", 54900, discount),   # Rs 549 / month
            "USD": _price_pair("USD", 899, discount),     # $8.99 / month
        },
        "quota": {"videos": 8, "period": "month"},
        "max_seconds": 60,
        "features": [
            "8 videos per month",
            "Videos up to 60 seconds",
            "Depth (2.5D) camera motion",
            "No watermark",
            "Commercial use",
        ],
    }
    studio = {
        "id": "studio",
        "name": "Studio",
        "tagline": "For channels and small teams.",
        "tier": 2,
        "prices": {
            "INR": _price_pair("INR", 129900, discount),  # Rs 1,299 / month
            "USD": _price_pair("USD", 1999, discount),    # $19.99 / month
        },
        "quota": {"videos": 16, "period": "month"},
        "max_seconds": 75,
        "features": [
            "16 videos per month",
            "Videos up to 75 seconds",
            "Depth (2.5D) camera motion",
            "Highest render priority",
            "Commercial use",
            "Email support",
        ],
    }
    return {"free": free, "creator": creator, "studio": studio}


_catalog_cache = None


def catalog() -> dict:
    """Plan catalog, overridable with BILLING_PLANS_JSON."""
    global _catalog_cache
    if _catalog_cache is not None:
        return _catalog_cache
    raw = os.environ.get("BILLING_PLANS_JSON", "").strip()
    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict) and parsed:
                _catalog_cache = parsed
                return _catalog_cache
        except json.JSONDecodeError:
            # A broken override must not take the whole API down; fall back.
            pass
    _catalog_cache = _default_catalog()
    return _catalog_cache


def plan(plan_id: str) -> dict:
    return catalog().get(plan_id) or catalog()["free"]


def paid_plan_ids() -> list:
    return [pid for pid, p in catalog().items() if p.get("tier", 0) > 0]


# ---------------------------------------------------------------- quota

def free_allowance() -> tuple:
    """(videos, period) for the free tier. Default 2 videos per month.

    Monthly rather than weekly on purpose: each free video is real money (a
    30 s video is ~4 paid images). Two a week is 8.7 a month and costs about
    four times what two a month does, with no extra signups to show for it.
    """
    try:
        videos = int(os.environ.get("BILLING_FREE_VIDEOS", "2"))
    except ValueError:
        videos = 2
    period = os.environ.get("BILLING_FREE_PERIOD", "month").strip().lower()
    if period not in ("day", "week", "month"):
        period = "month"
    return max(videos, 0), period


def quota_for(plan_id: str) -> tuple:
    """(videos, period, max_seconds) allowed for a plan.

    The free tier's allowance is configurable because it is a marketing lever,
    not a product constant. Paid tiers are explicit in the catalog.
    """
    p = plan(plan_id)
    if p.get("tier", 0) == 0:
        videos, period = free_allowance()
        return videos, period, int(p.get("max_seconds", 45))
    quota = p.get("quota") or {}
    return (int(quota.get("videos", 30)), quota.get("period", "month"),
            int(p.get("max_seconds", 75)))


def period_key(period: str, now: datetime | None = None) -> str:
    """Bucket key used to count usage inside the current quota window.

    Stored on the usage row so a count is always scoped to one window and a
    new window starts a fresh count with no scheduled job.
    """
    now = now or datetime.now(timezone.utc)
    if period == "day":
        return now.strftime("%Y-%m-%d")
    if period == "month":
        return now.strftime("%Y-%m")
    year, week, _ = now.isocalendar()
    return f"{year}-W{week:02d}"


def period_label(period: str) -> str:
    return {"day": "day", "week": "week", "month": "month"}.get(period, "week")


def period_start(period: str, now: datetime | None = None) -> datetime:
    """First instant of the current quota window, in UTC.

    Used to derive usage from existing rows (completed renders) when no dedicated
    counter row exists, so the quota works before any billing migration is run.
    """
    now = now or datetime.now(timezone.utc)
    if period == "day":
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    if period == "month":
        return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return start_of_day - timedelta(days=now.weekday())


def period_reset(period: str, now: datetime | None = None) -> str:
    """ISO timestamp when the current window ends (when the count resets)."""
    now = now or datetime.now(timezone.utc)
    start = period_start(period, now)
    if period == "day":
        end = start + timedelta(days=1)
    elif period == "month":
        end = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
    else:
        end = start + timedelta(days=7)
    return end.isoformat()


# ---------------------------------------------------------------- display

def _format_minor(minor: int, currency: str) -> str:
    units = MINOR_UNITS.get(currency, 100)
    symbol = CURRENCY_SYMBOL.get(currency, "")
    major = minor / units
    if currency == "INR":
        # Indian grouping is not worth a dependency here; whole rupees read fine.
        return f"{symbol}{major:,.0f}" if major == int(major) else f"{symbol}{major:,.2f}"
    return f"{symbol}{major:.2f}" if major % 1 else f"{symbol}{major:,.0f}"


def savings_percent(month_minor: int, year_minor: int) -> int:
    """How much the annual plan saves versus paying monthly for 12 months."""
    if month_minor <= 0:
        return 0
    full = month_minor * 12
    return int(round((1 - year_minor / full) * 100))


def public_plans(currency: str = "USD") -> list:
    """Plans shaped for the pricing page, in the visitor's currency."""
    currency = (currency or "USD").upper()
    if currency not in CURRENCY_SYMBOL:
        currency = "USD"
    out = []
    for p in sorted(catalog().values(), key=lambda x: x.get("tier", 0)):
        prices = (p.get("prices") or {}).get(currency) or {"month": 0, "year": 0}
        videos, period, max_seconds = quota_for(p["id"])
        out.append({
            "id": p["id"],
            "name": p.get("name", p["id"]),
            "tagline": p.get("tagline", ""),
            "tier": p.get("tier", 0),
            "popular": bool(p.get("popular")),
            "currency": currency,
            "month": prices.get("month", 0),
            "year": prices.get("year", 0),
            "month_display": _format_minor(prices.get("month", 0), currency),
            "year_display": _format_minor(prices.get("year", 0), currency),
            "year_per_month_display": _format_minor(
                int(round(prices.get("year", 0) / 12)), currency),
            "savings_percent": savings_percent(prices.get("month", 0), prices.get("year", 0)),
            "videos": videos,
            "period": period,
            "period_label": period_label(period),
            "max_seconds": max_seconds,
            "features": p.get("features", []),
            "provider": provider_for(currency) if p.get("tier", 0) > 0 else "",
            "checkout_ready": bool(p.get("tier", 0) > 0 and provider_for(currency)),
        })
    return out


def describe(plan_id: str, currency: str = "USD") -> dict:
    for entry in public_plans(currency):
        if entry["id"] == plan_id:
            return entry
    return public_plans(currency)[0]
