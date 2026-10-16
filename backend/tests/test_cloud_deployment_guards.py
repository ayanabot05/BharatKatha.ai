import os
import asyncio
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import cloud_render_dispatch
import cloud_render_worker
import cloud_scene_dispatch
import cloud_scene_worker
import cloud_identity
import piper_tts
import supertonic_tts


class CloudDeploymentGuards(unittest.TestCase):
    def test_production_rejects_local_voice_routes(self):
        voice = {"te": {"url": "http://127.0.0.1:5008", "model_id": "padmavathi",
                        "model_revision": "sha256:test", "license_url": "https://example.org/license",
                        "hardware_requirements": "CPU", "license_status": "verified-commercial"}}
        import json
        with patch.dict(os.environ, {"APP_ENV": "production", "PIPER_VOICES_JSON": json.dumps(voice)}, clear=False):
            with self.assertRaisesRegex(RuntimeError, "remote HTTPS"):
                piper_tts.voices()
        with patch.dict(os.environ, {"APP_ENV": "production", "SUPERTONIC_HINDI_SERVICE_URL": ""}, clear=False):
            self.assertFalse(supertonic_tts.available())

    def test_production_piper_requires_identity_audience(self):
        voice = {"te": {"url": "https://voice.example.run.app", "model_id": "padmavathi",
                        "model_revision": "sha256:test", "license_url": "https://example.org/license",
                        "hardware_requirements": "CPU", "license_status": "verified-commercial"}}
        import json
        with patch.dict(os.environ, {"APP_ENV": "production", "PIPER_VOICES_JSON": json.dumps(voice)}, clear=False):
            with self.assertRaisesRegex(RuntimeError, "identity authentication"):
                piper_tts.voices()

    def test_render_job_name_requires_complete_configuration(self):
        with patch.dict(os.environ, {"GOOGLE_CLOUD_PROJECT": "ayana-video-studio",
                                  "GOOGLE_CLOUD_REGION": "asia-south1",
                                  "CLOUD_RENDER_JOB": "bharatkatha-render"}, clear=False):
            self.assertEqual(cloud_render_dispatch.job_name(),
                             "projects/ayana-video-studio/locations/asia-south1/jobs/bharatkatha-render")
        with patch.dict(os.environ, {"CLOUD_RENDER_JOB": ""}, clear=False):
            with self.assertRaisesRegex(RuntimeError, "incomplete"):
                cloud_render_dispatch.job_name()

    def test_english_has_pinned_supertonic_signature(self):
        with patch.object(supertonic_tts, "available", return_value=True):
            self.assertIn("supertonic-3/M1", supertonic_tts.model_signature("en"))

    def test_private_voice_header_uses_service_audience(self):
        with patch.object(cloud_identity, "_token", return_value="test-id-token") as token:
            self.assertEqual(asyncio.run(cloud_identity.headers("https://voice.example.run.app")),
                             {"Authorization": "Bearer test-id-token"})
            token.assert_called_once_with("https://voice.example.run.app")

    def test_render_dispatch_uses_authenticated_google_api_and_owner_id(self):
        response = MagicMock()
        response.json.return_value = {"name": "projects/p/locations/r/operations/o"}
        session = MagicMock()
        session.post.return_value = response
        with patch.dict(os.environ, {"GOOGLE_CLOUD_PROJECT": "ayana-video-studio",
                                  "GOOGLE_CLOUD_REGION": "asia-south1",
                                  "CLOUD_RENDER_JOB": "bharatkatha-render"}, clear=False), \
             patch("google.auth.default", return_value=(object(), "ayana-video-studio")), \
             patch("google.auth.transport.requests.AuthorizedSession", return_value=session):
            self.assertEqual(cloud_render_dispatch.start("project-1", "owner-1", "claim-1"),
                             "projects/p/locations/r/operations/o")
        args, kwargs = session.post.call_args
        self.assertEqual(args[0], "https://run.googleapis.com/v2/projects/ayana-video-studio/locations/asia-south1/jobs/bharatkatha-render:run")
        self.assertEqual(kwargs["json"]["overrides"]["containerOverrides"][0]["env"],
                         [{"name": "RENDER_PROJECT_ID", "value": "project-1"},
                          {"name": "RENDER_USER_ID", "value": "owner-1"},
                          {"name": "RENDER_CLAIM_TOKEN", "value": "claim-1"}])
        session.close.assert_called_once()

    def test_render_worker_rejects_project_not_owned_by_dispatch_user(self):
        find_one = AsyncMock(return_value=None)
        render = AsyncMock()
        fake_core = SimpleNamespace(db=SimpleNamespace(projects=SimpleNamespace(find_one=find_one)))
        fake_projects = SimpleNamespace(_render_job=render)
        with patch.dict(sys.modules, {"core": fake_core, "projects": fake_projects}), \
             patch.dict(os.environ, {"RENDER_PROJECT_ID": "project-1", "RENDER_USER_ID": "owner-1",
                                  "RENDER_CLAIM_TOKEN": "claim-1"}):
            with self.assertRaisesRegex(RuntimeError, "owned by another user"):
                asyncio.run(cloud_render_worker.main())
        find_one.assert_awaited_once_with({"id": "project-1", "user_id": "owner-1"}, {"_id": 0})
        render.assert_not_awaited()

    def test_scene_dispatch_uses_authenticated_google_api(self):
        response = MagicMock()
        response.json.return_value = {"name": "scene-operation"}
        session = MagicMock()
        session.post.return_value = response
        with patch.dict(os.environ, {"GOOGLE_CLOUD_PROJECT": "ayana-video-studio",
                                  "GOOGLE_CLOUD_REGION": "asia-south1",
                                  "CLOUD_SCENE_JOB": "bharatkatha-scenes"}, clear=False), \
             patch("google.auth.default", return_value=(object(), "ayana-video-studio")), \
             patch("google.auth.transport.requests.AuthorizedSession", return_value=session):
            self.assertEqual(cloud_scene_dispatch.start("p", "u", "s", "lease-1"), "scene-operation")
        args, kwargs = session.post.call_args
        self.assertEqual(args[0], "https://run.googleapis.com/v2/projects/ayana-video-studio/locations/asia-south1/jobs/bharatkatha-scenes:run")
        self.assertEqual(kwargs["json"]["overrides"]["containerOverrides"][0]["env"][-1],
                         {"name": "SCENE_LEASE_TOKEN", "value": "lease-1"})

    def test_scene_worker_rejects_cross_user_request(self):
        find_one = AsyncMock(return_value=None)
        generate = AsyncMock()
        fake_core = SimpleNamespace(db=SimpleNamespace(projects=SimpleNamespace(find_one=find_one)),
                                    get_object=AsyncMock())
        fake_projects = SimpleNamespace(_all_scenes_job=generate, _single_scene_job=generate,
                                        best_scene_reference=MagicMock(), mark_scene_status=AsyncMock(), upd=AsyncMock())
        with patch.dict(sys.modules, {"core": fake_core, "projects": fake_projects}), \
             patch.dict(os.environ, {"SCENE_PROJECT_ID": "project-1", "SCENE_USER_ID": "owner-1",
                                  "SCENE_ID": "", "SCENE_LEASE_TOKEN": "lease-1"}):
            with self.assertRaisesRegex(RuntimeError, "owned by another user"):
                asyncio.run(cloud_scene_worker.main())
        find_one.assert_awaited_once_with({"id": "project-1", "user_id": "owner-1"}, {"_id": 0})
        generate.assert_not_awaited()

    def test_analytics_failure_is_noncritical_after_dispatch(self):
        import projects
        with patch.object(projects.pulse, "log_event", new=AsyncMock(side_effect=RuntimeError("analytics unavailable"))):
            asyncio.run(projects.log_noncritical_event("owner", "render_started", "en", "", project_id="p"))

    def test_ambiguous_scene_dispatch_keeps_claim_for_worker_or_expiry(self):
        import projects
        from db_supabase import ProjectsCollection
        project = {"approved": True, "style": "paint", "render": {"status": "idle"},
                   "scenes": [{"id": "s1", "status": "pending"}], "step": 3, "language": "te"}
        with patch.dict(os.environ, {"APP_ENV": "production"}), \
             patch.object(projects, "owned", new=AsyncMock(return_value=project)), \
             patch.object(projects, "check_daily_limit", new=AsyncMock()), \
             patch.object(projects, "mark_scene_status", new=AsyncMock()), \
             patch.object(projects, "upd", new=AsyncMock()), \
             patch.object(ProjectsCollection, "claim_scene_job", new=AsyncMock(return_value=True)), \
             patch.object(ProjectsCollection, "release_scene_job", new=AsyncMock()) as release, \
             patch.object(cloud_scene_dispatch, "start", side_effect=TimeoutError("response lost")):
            with self.assertRaises(TimeoutError):
                asyncio.run(projects.gen_scenes("p", {"id": "u"}))
        release.assert_not_awaited()

    def test_ambiguous_render_dispatch_keeps_claim_for_worker_or_expiry(self):
        import projects
        from db_supabase import ProjectsCollection
        project = {"approved": True, "render": {"status": "idle"},
                   "audio": {"path": "a.mp3"},
                   "scenes": [{"id": "s1", "status": "ready", "image_path": "s.jpg", "approved": True}],
                   "language": "en"}
        with patch.dict(os.environ, {"APP_ENV": "production"}), \
             patch.object(projects, "owned", new=AsyncMock(return_value=project)), \
             patch.object(projects, "review_is_current", return_value=True), \
             patch.object(projects, "assert_audio_idle"), \
             patch.object(projects, "check_daily_limit", new=AsyncMock()), \
             patch.object(ProjectsCollection, "claim_render_job", new=AsyncMock(return_value=True)), \
             patch.object(ProjectsCollection, "fail_render_claim", new=AsyncMock()) as fail, \
             patch.object(cloud_render_dispatch, "start", side_effect=TimeoutError("response lost")):
            with self.assertRaises(TimeoutError):
                asyncio.run(projects.start_render("p", {"id": "u"}))
        fail.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
