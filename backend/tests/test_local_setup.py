import asyncio
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

import core
import ai
import server
import projects
from fastapi import HTTPException, Response
from httpx import ASGITransport, AsyncClient


class LocalSetupTests(unittest.TestCase):
    def test_provider_timeout_is_actionable(self):
        async def check():
            with patch.object(ai, "_text_models", new=AsyncMock(side_effect=asyncio.TimeoutError)):
                with self.assertRaisesRegex(RuntimeError, "took too long"):
                    await ai._text("system", "prompt")
        asyncio.run(check())

    def test_review_rejects_string_safety_decision(self):
        async def check():
            with patch.object(ai, "ask_json", new=AsyncMock(return_value={"score": 90, "safe": "false"})):
                with self.assertRaises(RuntimeError):
                    await ai._agent("safety", "Safety", "Review", {}, "te", "Andhra Pradesh")
        asyncio.run(check())

    def test_review_rejects_unstructured_response(self):
        async def check():
            with patch.object(ai, "ask_json", new=AsyncMock(return_value=["looks good"])):
                with self.assertRaises(RuntimeError):
                    await ai._agent("hook", "Hook", "Review", {}, "te", "Andhra Pradesh")
        asyncio.run(check())

    def test_concept_review_requires_boolean_alignment(self):
        async def check():
            with patch.object(ai, "ask_json", new=AsyncMock(return_value={"score": 90, "aligned": "false"})):
                with self.assertRaisesRegex(RuntimeError, "concept-alignment"):
                    await ai._agent("concept", "Concept", "Compare", {}, "en", "Hyderabad", "village repair")
        asyncio.run(check())

    def test_concept_miss_blocks_overall_approval(self):
        async def agent(key, name, brief, script, language, region, idea):
            self.assertEqual(idea, "village pipe repair")
            return {"key": key, "name": name, "score": 90, "fixes": [],
                    **({"aligned": False, "misses": ["Repair never appears"]} if key == "concept" else {}),
                    **({"safe": True} if key == "safety" else {})}
        async def check():
            good_checks = {"all_passed": True, "safety_passed": True, "checks": [],
                           "fixes": [], "disclaimer": "Text estimate"}
            with patch.object(ai, "_agent", side_effect=agent), \
                 patch.object(ai.ram_ai, "run_ram_ai_checks", return_value=good_checks):
                result = await ai.validate_script({"scenes": []}, "en", "Hyderabad", 30, "village pipe repair")
            self.assertFalse(result["concept_aligned"])
            self.assertFalse(result["all_passed"])
            self.assertIn("Repair never appears", result["fixes"])
        asyncio.run(check())

    def test_script_edit_invalidates_previous_review_and_outputs(self):
        async def check():
            previous = {"scenes": [], "render": {"status": "done"}, "language": "te", "region": "Andhra Pradesh"}
            with patch.object(projects, "owned", new=AsyncMock(return_value=previous)), \
                 patch.object(projects, "upd", new=AsyncMock()) as update, \
                 patch.object(projects.pulse, "log_event", new=AsyncMock()):
                await projects.patch("test-project", projects.ProjectPatch(script={"scenes": []}), {"id": "test-user"})
                fields = update.call_args.kwargs
                self.assertIsNone(fields["validation"])
                self.assertIsNone(fields["audio"])
                self.assertFalse(fields["approved"])
                self.assertEqual(fields["render"]["status"], "idle")
        asyncio.run(check())

    def test_script_edit_rejected_during_render(self):
        async def check():
            with patch.object(projects, "owned", new=AsyncMock(return_value={"render": {"status": "rendering"}})), \
                 patch.object(projects, "upd", new=AsyncMock()) as update:
                with self.assertRaises(HTTPException) as caught:
                    await projects.patch("test-project", projects.ProjectPatch(script={"scenes": []}), {"id": "test-user"})
                self.assertEqual(caught.exception.status_code, 409)
                update.assert_not_awaited()
        asyncio.run(check())

    def test_script_approval_rejects_failed_quality_checks(self):
        async def check():
            project = {"validation": {"safe": True, "all_passed": False}, "step": 2}
            with patch.object(projects, "owned", new=AsyncMock(return_value=project)), \
                 patch.object(projects, "upd", new=AsyncMock()) as update:
                with self.assertRaises(HTTPException) as caught:
                    await projects.approve("test-project", {"id": "test-user"})
                self.assertEqual(caught.exception.status_code, 400)
                update.assert_not_awaited()
        asyncio.run(check())

    def test_scene_change_invalidates_script_approval(self):
        async def check():
            project = {"scenes": [{"id": "scene-1", "narration": "old", "visual": "old visual"}],
                       "script": {"scenes": []}, "render": {"status": "idle"},
                       "validation": {"all_passed": True}, "approved": True}
            with patch.object(projects, "owned", new=AsyncMock(return_value=project)), \
                 patch.object(projects, "upd", new=AsyncMock()) as update, \
                 patch.object(projects, "db") as fake_db:
                fake_db.projects.update_one = AsyncMock()
                await projects.patch_scene("test-project", "scene-1",
                                           projects.SceneTextIn(narration="new", visual="old visual"),
                                           {"id": "test-user"})
                self.assertIsNone(update.call_args.kwargs["validation"])
                self.assertFalse(update.call_args.kwargs["approved"])
        asyncio.run(check())

    def test_render_rejects_stale_script_review(self):
        async def check():
            with patch.object(projects, "owned", new=AsyncMock(return_value={"approved": False,
                                                                             "validation": {"all_passed": True}})):
                with self.assertRaisesRegex(HTTPException, "Review and approve"):
                    await projects.start_render("test-project", {"id": "test-user"})
        asyncio.run(check())

    def test_storage_roundtrip_and_traversal(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            with patch.object(core, "STORAGE_ROOT", Path(directory)):
                core.init_storage()
                core._put("vidbharat/images/test/image.png", b"image", "image/png")
                self.assertEqual(core._get("vidbharat/images/test/image.png"), (b"image", "image/png"))
                with self.assertRaises(HTTPException):
                    core._get("../outside")
                with self.assertRaises(HTTPException):
                    core._get("missing.png")

    def test_local_and_production_cookies(self):
        for secure in (False, True):
            with patch.dict(os.environ, {"COOKIE_SECURE": str(secure).lower()}):
                response = Response()
                core.set_auth_cookies(response, "test-user")
                cookie = response.headers.getlist("set-cookie")[0]
                self.assertEqual("Secure" in cookie, secure)
                self.assertIn("SameSite=none" if secure else "SameSite=lax", cookie)
                self.assertIn("HttpOnly", cookie)

    def test_missing_provider_keys_are_actionable(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "", "OPENAI_API_KEY": ""}):
            for key in ("GEMINI_API_KEY", "OPENAI_API_KEY"):
                with self.assertRaisesRegex(RuntimeError, key):
                    ai._key(key)

    def test_text_quota_is_detected_before_model_fallback(self):
        class QuotaError(Exception):
            code = 429
        self.assertTrue(ai._is_text_quota_error(QuotaError("limited")))
        self.assertTrue(ai._is_text_quota_error(RuntimeError("RESOURCE_EXHAUSTED")))
        self.assertFalse(ai._is_text_quota_error(RuntimeError("temporary 503")))

    def test_health_and_anonymous_auth(self):
        async def check():
            async with AsyncClient(transport=ASGITransport(app=server.app), base_url="http://localhost:8000") as client:
                response = await client.get("/api/health", headers={"Origin": "http://localhost:3003"})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.headers["access-control-allow-origin"], "http://localhost:3003")
                self.assertEqual((await client.get("/api/auth/me")).status_code, 401)
                self.assertEqual((await client.post("/api/auth/refresh")).status_code, 401)
                response = await client.post("/api/auth/logout")
                self.assertEqual(response.status_code, 200)
                self.assertIn("Max-Age=0", response.headers["set-cookie"])
        asyncio.run(check())
