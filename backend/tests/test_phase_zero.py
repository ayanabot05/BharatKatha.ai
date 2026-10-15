import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
import pytest
from pydantic import ValidationError
from httpx import ASGITransport, AsyncClient
import server
import projects
import beta_controls
import ai


def run(coro):
    return asyncio.run(coro)


def test_missing_coach_metrics_are_unknown_and_negative_counts_rejected():
    data = server.CoachIn(videos=[{"title": "My next story"}]).model_dump()
    assert data["videos"][0]["views"] is None
    assert data["subscribers"] is None
    with pytest.raises(ValidationError):
        server.VideoStat(title="Story", views=-1)
    with pytest.raises(ValidationError):
        server.VideoStat(title="Story", viewed_vs_swiped_pct=101)


def test_coach_does_not_present_invented_measurements_without_metrics():
    async def check():
        with patch.object(ai, "ask_json", new=AsyncMock(return_value={"summary": "Try a clear opening", "health_score": 95, "measured": ["Made up number"]})):
            result = await ai.coach({"videos": [{"title": "Story", "views": None, "retention": [None]}]})
            assert result["health_score"] is None and result["measured"] == []
    run(check())


def test_changed_narration_does_not_reuse_approved_picture():
    old = [{"id": "old", "visual": "A farmer", "narration": "He plants rice", "image_path": "rice.png", "approved": True}]
    result = projects.scenes_from_script({"scenes": [{"visual": "A farmer", "narration": "He harvests rice"}]}, old)
    assert not result[0]["approved"] and result[0]["image_path"] is None
    same = projects.scenes_from_script({"scenes": old}, old)
    assert same[0]["image_path"] == "rice.png"


def test_brief_is_in_review_and_invalidates_approval():
    p = {"idea": "Repair a leak", "brief": {"category": "Practical", "audience": "Farmers", "platform": "Shorts"}}
    assert "Farmers" in projects.requested_content(p)
    assert projects.review_fingerprint(p) != projects.review_fingerprint({**p, "brief": {"audience": "Kids"}})


def test_feedback_cannot_attach_to_another_users_project():
    async def check():
        with patch.object(server, "db", SimpleNamespace(projects=SimpleNamespace(find_one=AsyncMock(return_value=None)))):
            with pytest.raises(server.HTTPException) as error:
                await server.feedback(server.FeedbackIn(project_id="someone-else", rating=3, area="Story", comment="Missing ending"), {"id": "me"})
            assert error.value.status_code == 404
    run(check())


def test_feedback_is_unreviewed_and_not_training_opted_in_by_default():
    async def check():
        save = AsyncMock()
        with patch.object(server, "db", SimpleNamespace(pulse_events=SimpleNamespace(insert_one=save))):
            result = await server.feedback(server.FeedbackIn(rating=4, area="Voice", comment="A pause is too long"), {"id": "me"})
            assert result["saved"]
            meta = save.call_args.args[0]["meta"]
            assert meta["reviewed"] is False and meta["permission_to_train"] is False
    run(check())


def test_rate_limit_returns_retry_after_and_stops_handler():
    async def check():
        with patch.dict(server.os.environ, {"RATE_LIMIT_ENABLED": "true"}), patch.object(beta_controls, "consume", new=AsyncMock(return_value=(False, 20))):
            async with AsyncClient(transport=ASGITransport(app=server.app), base_url="http://test") as c:
                response = await c.post("/api/auth/register", json={})
                assert response.status_code == 429
                assert response.headers["retry-after"] == "20"
    run(check())


def test_foreign_origin_cannot_write_and_api_is_not_publicly_cached():
    async def check():
        async with AsyncClient(transport=ASGITransport(app=server.app), base_url="http://test") as c:
            response = await c.post("/api/auth/logout", headers={"origin": "https://untrusted.example"})
            assert response.status_code == 403
            health = await c.get("/api/health")
            assert health.headers["cache-control"] == "private, no-store"
    run(check())
