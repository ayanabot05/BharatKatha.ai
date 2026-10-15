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
                 patch.object(ai, "adjudicate_story_gaps", new=AsyncMock(return_value=["Repair never appears"])), \
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

    def test_thumbnail_does_not_invalidate_script_review(self):
        project = {
            "id": "p-1",
            "idea": "Anantapur water",
            "language": "te",
            "region": "Andhra Pradesh",
            "duration": 45,
            "script": {"title": "నీరు", "scenes": [{"narration": "నీరు లేదు", "visual": "dry"}]},
            "scenes": [{"id": "s-1", "image_path": "vidbharat/scenes/u/s1.jpg", "placeholder": False, "approved": True}],
        }
        fp = projects.review_fingerprint(project)
        project["validation"] = {"all_passed": True, "content_fingerprint": fp}
        project["approved"] = True
        self.assertTrue(projects.review_is_current(project))

        # Adding thumbnail metadata to script
        project["script"]["thumbnail_path"] = "vidbharat/thumbnails/u/thumb.png"
        project["script"]["thumbnail_scene_id"] = "s-1"
        project["script"]["thumbnail_title"] = "నీరు కథ"
        # Must still be current!
        self.assertTrue(projects.review_is_current(project))

    def test_project_delete_cleans_files_and_pulse(self):
        async def check():
            project = {
                "id": "p-del", "user_id": "u-1",
                "scenes": [{"image_path": "p1.jpg", "versions": ["p1.jpg", "p0.jpg"], "audio_path": "a1.mp3"}],
                "audio": {"path": "combined.mp3"},
                "render": {"video_path": "final.mp4"},
                "script": {"thumbnail_path": "thumb.png"},
            }
            fake_db = unittest.mock.MagicMock()
            fake_db.projects.delete_one = AsyncMock()
            fake_db.files.update_many = AsyncMock()
            fake_db.pulse_events.delete_many = AsyncMock()
            with patch.object(projects, "owned", new=AsyncMock(return_value=project)), \
                 patch.object(projects, "db", fake_db):
                res = await projects.delete("p-del", {"id": "u-1"})
                self.assertEqual(res, {"ok": True})
                fake_db.projects.delete_one.assert_awaited_once_with({"id": "p-del"})
                fake_db.files.update_many.assert_awaited_once()
                marked_paths = fake_db.files.update_many.call_args[0][0]["storage_path"]["$in"]
                for expected in ("p1.jpg", "p0.jpg", "a1.mp3", "combined.mp3", "final.mp4", "thumb.png"):
                    self.assertIn(expected, marked_paths)
                fake_db.pulse_events.delete_many.assert_awaited_once_with({"project_id": "p-del"})
        asyncio.run(check())

    def test_owned_auto_heals_stuck_rendering_and_generating(self):
        async def check():
            stuck_project = {
                "id": "p-stuck", "user_id": "u-1",
                "render": {"status": "rendering", "progress": 40},
                "scenes": [
                    {"id": "s-1", "status": "generating"},
                    {"id": "s-2", "status": "ready"},
                    {"id": "s-3", "status": "queued"},
                ],
            }
            fake_db = unittest.mock.MagicMock()
            fake_db.projects.find_one = AsyncMock(return_value=stuck_project)
            with patch.object(projects, "db", fake_db), \
                 patch.object(projects, "upd", new=AsyncMock()) as mock_upd:
                # Ensure no active tasks
                projects._active_renders.discard("p-stuck")
                projects._active_generations.discard("p-stuck")
                healed = await projects.owned("p-stuck", {"id": "u-1"})
                self.assertEqual(healed["render"]["status"], "failed")
                self.assertIn("interrupted", healed["render"]["message"].lower())
                self.assertEqual(healed["scenes"][0]["status"], "failed")
                self.assertEqual(healed["scenes"][1]["status"], "ready")
                self.assertEqual(healed["scenes"][2]["status"], "failed")
                mock_upd.assert_awaited_once()
        asyncio.run(check())


    def test_pulse_endpoints_require_admin_role(self):
        async def check():
            regular_user = {"id": "u-reg", "role": "user", "email": "reg@example.com"}
            admin_user = {"id": "u-adm", "role": "admin", "email": "adm@example.com"}
            with self.assertRaises(HTTPException) as ctx:
                await server.pulse_weekly("te", "AP", user=regular_user)
            self.assertEqual(ctx.exception.status_code, 403)

            with self.assertRaises(HTTPException) as ctx:
                await server.pulse_report(user=regular_user)
            self.assertEqual(ctx.exception.status_code, 403)

            with patch.object(server.pulse, "weekly_pulse", new=AsyncMock(return_value={"total_events": 5})), \
                 patch.object(server.pulse, "learning_report", new=AsyncMock(return_value={"total_events": 5})):
                w = await server.pulse_weekly("te", "AP", user=admin_user)
                self.assertEqual(w["total_events"], 5)
                r = await server.pulse_report(user=admin_user)
                self.assertEqual(r["total_events"], 5)
        asyncio.run(check())

    def test_daily_limits_enforced_for_users_bypassed_for_admin(self):
        async def check():
            regular_user = {"id": "u-reg", "role": "user"}
            admin_user = {"id": "u-adm", "role": "admin"}
            fake_db = unittest.mock.MagicMock()

            # Under limit: count = 5 < 15
            fake_db.pulse_events.count_documents = AsyncMock(return_value=5)
            with patch.object(projects, "db", fake_db):
                await projects.check_daily_limit(regular_user, "script_generated")

            # At/over limit: count = 15 >= 15 -> 429
            fake_db.pulse_events.count_documents = AsyncMock(return_value=15)
            with patch.object(projects, "db", fake_db):
                with self.assertRaises(HTTPException) as ctx:
                    await projects.check_daily_limit(regular_user, "script_generated")
                self.assertEqual(ctx.exception.status_code, 429)
                self.assertIn("Daily limit reached", ctx.exception.detail)

            # Admin bypasses even if count would be huge
            fake_db.pulse_events.count_documents = AsyncMock(return_value=999)
            with patch.object(projects, "db", fake_db):
                await projects.check_daily_limit(admin_user, "script_generated")
                fake_db.pulse_events.count_documents.assert_not_called()
        asyncio.run(check())

