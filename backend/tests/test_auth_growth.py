"""Isolated administrators, password reset, early-access sign-ups and the
first-party analytics funnel.

The database is faked at the same seams the app uses (``store`` and, for the
login throttle, ``admin_auth``), so these tests exercise the real logic without
a live Postgres.
"""
import asyncio
import functools
import hashlib
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

import admin_auth
import auth_api
import core
import early_access
import growth
import store


def async_test(fn):
    """Run an async test without adding pytest-asyncio to the project."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        return asyncio.run(fn(*args, **kwargs))
    return wrapper


def _request(**cookies):
    return SimpleNamespace(cookies=cookies,
                           client=SimpleNamespace(host="10.0.0.9"))


# --------------------------------------------------------------- admin isolation

def test_admin_dependency_rejects_a_missing_cookie():
    async def check():
        with pytest.raises(HTTPException) as err:
            await admin_auth.require_admin(_request())
        assert err.value.status_code == 401
    asyncio.run(check())


@pytest.mark.parametrize("kind", ["access", "refresh"])
def test_user_tokens_cannot_open_the_admin_surface(kind):
    """A user session is not an administrator session, whatever it claims."""
    async def check():
        token = core.make_token("u-1", kind, timedelta(minutes=15))
        with patch.object(admin_auth, "find_by_id", new=AsyncMock(
                return_value={"id": "u-1", "role": "admin"})):
            with pytest.raises(HTTPException) as err:
                await admin_auth.require_admin(_request(admin_token=token))
        assert err.value.status_code == 401
    asyncio.run(check())


def test_admin_token_opens_the_admin_surface():
    async def check():
        token = core.make_token("a-1", "admin", timedelta(hours=1))
        with patch.object(admin_auth, "find_by_id", new=AsyncMock(
                return_value={"id": "a-1", "email": "boss@example.com"})):
            rec = await admin_auth.require_admin(_request(admin_token=token))
        assert rec["id"] == "a-1"
    asyncio.run(check())


def test_ensure_admin_stores_a_bcrypt_hash_and_normalises_the_email():
    async def check():
        captured = {}

        async def fake_run(query, params=(), table=None):
            captured["params"] = params
            return True

        with patch.object(admin_auth.store, "run", new=AsyncMock(side_effect=fake_run)), \
             patch.object(admin_auth, "find_by_email", new=AsyncMock(return_value=None)):
            assert await admin_auth.ensure_admin("Boss@Example.COM", "secret-password")

        _, email, password_hash, _ = captured["params"]
        assert email == "boss@example.com"            # normalised for lookup
        assert password_hash != "secret-password"      # never stored in clear
        assert core.verify_password("secret-password", password_hash)
    asyncio.run(check())


def test_admin_sign_in_rejects_a_wrong_password_and_records_the_failure():
    async def check():
        rec = {"id": "a-1", "email": "boss@example.com",
               "password_hash": core.hash_password("right-password")}
        with patch.object(admin_auth, "_throttle", new=AsyncMock()), \
             patch.object(admin_auth, "_record_failure", new=AsyncMock()) as failure, \
             patch.object(admin_auth, "find_by_email", new=AsyncMock(return_value=rec)):
            with pytest.raises(HTTPException) as err:
                await admin_auth.authenticate("boss@example.com", "wrong-password", _request())
        assert err.value.status_code == 401
        failure.assert_awaited_once()
    asyncio.run(check())


def test_admin_sign_in_accepts_the_right_password():
    async def check():
        rec = {"id": "a-1", "email": "boss@example.com",
               "password_hash": core.hash_password("right-password")}
        with patch.object(admin_auth, "_throttle", new=AsyncMock()), \
             patch.object(admin_auth, "_clear_failures", new=AsyncMock()), \
             patch.object(admin_auth, "_record_failure", new=AsyncMock()) as failure, \
             patch.object(admin_auth.store, "run", new=AsyncMock(return_value=True)), \
             patch.object(admin_auth, "find_by_email", new=AsyncMock(return_value=rec)):
            got = await admin_auth.authenticate("boss@example.com", "right-password", _request())
        assert got["id"] == "a-1"
        failure.assert_not_awaited()
    asyncio.run(check())


# --------------------------------------------------------------- password reset

def test_reset_token_is_stored_only_as_a_hash():
    async def check():
        captured = {}

        async def fake_run(query, params=(), table=None):
            captured["params"] = params
            return True

        user = {"id": "u-1", "email": "a@example.com"}
        fake_db = SimpleNamespace(users=SimpleNamespace(find_one=AsyncMock(return_value=user)))
        with patch.object(auth_api.store, "using_sql", return_value=True), \
             patch.object(auth_api.store, "run", new=AsyncMock(side_effect=fake_run)), \
             patch.object(auth_api.store, "fetch_one", new=AsyncMock(return_value=None)), \
             patch.object(auth_api, "db", fake_db), \
             patch.object(auth_api.mailer, "send", new=AsyncMock(return_value=False)):
            out = await auth_api.forgot(auth_api.ForgotIn(email="a@example.com"),
                                        SimpleNamespace(client=SimpleNamespace(host="1.1.1.1")))

        token_hash, user_id = captured["params"]
        assert user_id == "u-1"
        assert len(token_hash) == 64                     # sha256 hex
        assert token_hash != "" and " " not in token_hash
        # No SMTP configured -> the operator must relay, and we say so.
        assert out["delivery"] == "manual"
    asyncio.run(check())


def test_forgot_does_not_reveal_whether_an_account_exists():
    async def check():
        fake_db = SimpleNamespace(users=SimpleNamespace(find_one=AsyncMock(return_value=None)))
        with patch.object(auth_api.store, "using_sql", return_value=True), \
             patch.object(auth_api.store, "run", new=AsyncMock()) as run, \
             patch.object(auth_api, "db", fake_db):
            out = await auth_api.forgot(auth_api.ForgotIn(email="nobody@example.com"),
                                        SimpleNamespace(client=SimpleNamespace(host="1.1.1.1")))
        assert out["sent"] is True
        run.assert_not_awaited()                         # nothing was created
    asyncio.run(check())


def test_forgot_is_honest_when_the_store_is_unavailable():
    async def check():
        with patch.object(auth_api.store, "using_sql", return_value=False):
            out = await auth_api.forgot(auth_api.ForgotIn(email="a@example.com"),
                                        SimpleNamespace(client=SimpleNamespace(host="1.1.1.1")))
        assert out["sent"] is False
        assert out["delivery"] == "unavailable"          # not a false "check your inbox"
    asyncio.run(check())


def test_reset_rejects_an_unknown_or_expired_token():
    async def check():
        with patch.object(auth_api.store, "fetch_one", new=AsyncMock(return_value=None)):
            with pytest.raises(HTTPException) as err:
                await auth_api.reset(auth_api.ResetIn(token="x" * 40, password="new-password"))
        assert err.value.status_code == 400
    asyncio.run(check())


def test_reset_sets_the_password_and_burns_every_outstanding_token():
    async def check():
        fake_db = SimpleNamespace(users=SimpleNamespace(update_one=AsyncMock()))
        with patch.object(auth_api.store, "fetch_one", new=AsyncMock(return_value={"user_id": "u-1"})), \
             patch.object(auth_api.store, "run", new=AsyncMock(return_value=True)) as run, \
             patch.object(auth_api, "db", fake_db):
            out = await auth_api.reset(auth_api.ResetIn(token="y" * 40, password="brand-new"))
        assert out["ok"] is True
        sets = fake_db.users.update_one.await_args.args[1]["$set"]
        assert core.verify_password("brand-new", sets["password_hash"])
        # A single statement burns this token and every other outstanding one.
        assert run.await_count == 1
        query = run.await_args.args[0]
        assert "used_at = NOW()" in query and "used_at IS NULL" in query
        assert run.await_args.args[1] == ("u-1",)
    asyncio.run(check())


def test_reset_stores_a_hash_of_the_token_that_was_handed_out():
    async def check():
        seen = {}

        async def fake_fetch(query, params=(), table=None):
            seen["hash"] = params[0]
            return None

        with patch.object(auth_api.store, "fetch_one", new=AsyncMock(side_effect=fake_fetch)):
            with pytest.raises(HTTPException):
                await auth_api.reset(auth_api.ResetIn(token="t" * 40, password="brand-new"))
        assert seen["hash"] == hashlib.sha256(("t" * 40).encode()).hexdigest()
    asyncio.run(check())


# --------------------------------------------------------------- analytics

def test_track_swallows_storage_failures():
    """Analytics must never be able to fail a user's request."""
    async def check():
        with patch.object(growth, "_suppressed", return_value=False), \
             patch.object(growth.store, "run", new=AsyncMock(side_effect=RuntimeError("db down"))):
            await growth.track("visit")  # must not raise
    asyncio.run(check())


def test_analytics_is_never_written_during_a_test_run():
    """The live funnel must never record fixture data from the suite."""
    async def check():
        with patch.object(growth.store, "run", new=AsyncMock()) as run:
            await growth.track("render_completed", user_id="owner-1", project_id="story-1")
        run.assert_not_awaited()
    asyncio.run(check())


def test_funnel_reports_ordered_stages_with_conversion():
    async def check():
        events = {"visit": 200, "signup": 50, "project_created": 40,
                  "script_approved": 20, "render_completed": 10, "download": 4}
        people = {k: v for k, v in events.items()}
        with patch.object(growth, "_counts", new=AsyncMock(side_effect=[events, people])):
            out = await growth.funnel(30)
        names = [s["name"] for s in out["stages"]]
        assert names == growth.FUNNEL
        first = out["stages"][0]
        assert first["events"] == 200 and first["from_top_pct"] == 100.0
        signup = out["stages"][1]
        assert signup["from_previous_pct"] == 25.0
        assert signup["from_top_pct"] == 25.0
    asyncio.run(check())


def test_client_may_only_report_the_visit_event():
    async def check():
        out = await growth.ingest(growth.EventIn(name="download"), _request())
        assert out["ok"] is False
        with patch.object(growth, "track", new=AsyncMock()) as track:
            out2 = await growth.ingest(growth.EventIn(name="visit", session_id="s1"), _request())
        assert out2["ok"] is True
        track.assert_awaited_once()
    asyncio.run(check())


def test_operator_email_list_replaces_the_role_bypass():
    with patch.dict("os.environ", {"OPERATOR_EMAILS": "op@example.com, second@example.com",
                                   "ADMIN_EMAIL": "boss@example.com"}, clear=False):
        assert core.is_operator({"email": "op@example.com"})
        assert core.is_operator({"email": "boss@example.com"})   # ADMIN_EMAIL is implicit
        assert not core.is_operator({"email": "someone@example.com"})
        assert not core.is_operator({})


# --------------------------------------------------------------- early access

def test_notify_reports_saved_when_persisted():
    async def check():
        with patch.object(early_access.store, "fetch_one", new=AsyncMock(return_value={"id": "n1"})):
            out = await early_access.notify(early_access.NotifyIn(email="Fan@Example.com"))
        assert out == {"saved": True, "already": False}
    asyncio.run(check())


def test_notify_detects_a_duplicate_without_claiming_a_new_signup():
    async def check():
        with patch.object(early_access.store, "using_sql", return_value=True), \
             patch.object(early_access.store, "fetch_one", new=AsyncMock(return_value=None)), \
             patch.object(early_access.store, "unavailable", return_value=False):
            out = await early_access.notify(early_access.NotifyIn(email="fan@example.com"))
        assert out == {"saved": True, "already": True}
    asyncio.run(check())


def test_notify_does_not_pretend_to_save_without_a_store():
    async def check():
        with patch.object(early_access.store, "using_sql", return_value=False), \
             patch.object(early_access.store, "fetch_one", new=AsyncMock(return_value=None)):
            out = await early_access.notify(early_access.NotifyIn(email="fan@example.com"))
        assert out["saved"] is False
    asyncio.run(check())


def test_unknown_topics_fall_back_to_the_supported_one():
    async def check():
        captured = {}

        async def fake_fetch(query, params=(), table=None):
            captured["params"] = params
            return {"id": "n1"}

        with patch.object(early_access.store, "fetch_one", new=AsyncMock(side_effect=fake_fetch)):
            await early_access.notify(early_access.NotifyIn(email="fan@example.com", topic="something-else"))
        assert captured["params"][2] == "ai_motion"
    asyncio.run(check())
