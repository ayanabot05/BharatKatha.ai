"""Currency resolution by geography.

India must see rupee pricing and everyone else USD, decided from the visitor's
country rather than from anything the browser can set. The important property
tested here is precedence: a real edge country header outranks a requested
currency, so nobody outside India can claim rupee pricing.

These tests are pure: they build real Starlette requests and call the resolver,
so no database and no running server are involved.
"""
from starlette.requests import Request

import billing_api


def make_request(headers=None):
    raw = [(str(k).lower().encode(), str(v).encode()) for k, v in (headers or {}).items()]
    return Request({"type": "http", "method": "GET", "path": "/api/billing/plans",
                    "headers": raw, "query_string": b""})


# ------------------------------------------------------------------ edge signal

def test_edge_header_decides_the_currency():
    assert billing_api.resolve_currency(make_request({"cf-ipcountry": "IN"})) == "INR"
    assert billing_api.resolve_currency(make_request({"cf-ipcountry": "US"})) == "USD"
    assert billing_api.resolve_currency(make_request({"cf-ipcountry": "GB"})) == "USD"
    assert billing_api.resolve_currency(make_request({"cf-ipcountry": "in"})) == "INR"


def test_every_supported_edge_header_is_read():
    for header in billing_api.EDGE_COUNTRY_HEADERS:
        assert billing_api.resolve_currency(make_request({header: "IN"})) == "INR", header


def test_unknown_edge_country_falls_through_instead_of_sticking():
    """XX means the edge could not tell. It must not block a later signal."""
    assert billing_api.resolve_currency(make_request({"cf-ipcountry": "XX"}), country_hint="IN") == "INR"
    assert billing_api.resolve_currency(make_request({"cf-ipcountry": "T1"})) == "USD"
    assert billing_api.resolve_currency(make_request({"cf-ipcountry": ""})) == "USD"


def test_edge_outranks_a_requested_currency():
    """The anti-arbitrage rule: geography beats whatever the client asks for."""
    assert billing_api.resolve_currency(
        make_request({"cf-ipcountry": "US"}), requested="INR") == "USD"
    assert billing_api.resolve_currency(
        make_request({"cf-ipcountry": "IN"}), requested="USD") == "INR"


def test_edge_outranks_the_browser_hint():
    assert billing_api.resolve_currency(
        make_request({"cf-ipcountry": "US"}), country_hint="IN") == "USD"


# ------------------------------------------------------------------ no edge

def test_browser_hint_is_used_when_no_edge_header_exists():
    """Local development and a directly served API have no edge header."""
    assert billing_api.resolve_currency(make_request(), country_hint="IN") == "INR"
    assert billing_api.resolve_currency(make_request(), country_hint="US") == "USD"
    assert billing_api.resolve_currency(make_request(), country_hint="") == "USD"


def test_requested_currency_beats_the_browser_hint():
    assert billing_api.resolve_currency(make_request(), requested="USD", country_hint="IN") == "USD"


def test_an_unsupported_requested_currency_is_ignored():
    assert billing_api.resolve_currency(make_request(), requested="EUR") == "USD"
    assert billing_api.resolve_currency(make_request(), requested="") == "USD"
    assert billing_api.resolve_currency(make_request(), requested="   ") == "USD"


# ------------------------------------------------------------------ reporting

def test_currency_source_names_the_signal_that_decided():
    """An operator can confirm edge geography is arriving on a live deploy."""
    assert billing_api.currency_source(make_request({"cf-ipcountry": "IN"})) == "edge"
    assert billing_api.currency_source(make_request(), requested="INR") == "requested"
    assert billing_api.currency_source(make_request(), country_hint="IN") == "browser_hint"
    assert billing_api.currency_source(make_request()) == "default"
    # Edge wins the label too, not just the currency.
    assert billing_api.currency_source(
        make_request({"cf-ipcountry": "IN"}), country_hint="US") == "edge"
