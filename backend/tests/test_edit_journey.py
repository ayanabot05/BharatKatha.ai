"""Workflow state tests with simulated providers. These do not certify media quality."""
import asyncio
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
import pytest
from fastapi import HTTPException
import projects
import ai


def story():
    scenes = [{"id": "s1", "visual": "A child sees a bird on a branch", "narration": "A bird rests on the branch.", "image_path": "one.png", "status": "ready", "approved": True, "versions": ["one.png"]},
              {"id": "s2", "visual": "The child watches the bird fly away", "narration": "The bird flies away.", "image_path": "two.png", "status": "ready", "approved": True, "versions": ["two.png"]}]
    p = {"id": "journey", "idea": "A child watches a bird", "language": "en", "region": "India", "style": "storybook", "step": 6, "scenes": scenes, "audio": {"path": "old.mp3"}, "render": {"status": "done", "video_path": "old.mp4"}, "approved": True}
    p["script"] = projects.script_with_scenes({}, scenes) or {"scenes": [{"visual": s["visual"], "narration": s["narration"]} for s in scenes]}
    p["validation"] = {"all_passed": True, "content_fingerprint": projects.review_fingerprint(p)}
    return p


class Memory:
    def __init__(self, p): self.p = p
    async def find_one(self, *a, **kw): return deepcopy(self.p)
    async def update_one(self, filt, update):
        target = next((s for s in self.p["scenes"] if s["id"] == filt.get("scenes.id")), self.p)
        for key, value in update.get("$set", {}).items(): target[key.replace("scenes.$.", "")] = value
        for key, value in update.get("$push", {}).items(): target.setdefault(key.replace("scenes.$.", ""), []).append(value)
    async def upd(self, pid, **fields): self.p.update(fields)


def test_voice_lock_releases_after_provider_failure():
    async def run():
        with patch.object(projects, "owned", AsyncMock(return_value=story())), patch.object(projects, "_audio_ai", AsyncMock(side_effect=RuntimeError("provider unavailable"))):
            with pytest.raises(RuntimeError): await projects.audio_ai("journey", projects.VoiceIn(), {"id":"tester"})
            assert "journey" not in projects._active_audio
    asyncio.run(run())


def test_story_edit_cannot_race_voice_generation():
    async def run():
        projects._active_audio.add("journey")
        try:
            with patch.object(projects, "owned", AsyncMock(return_value=story())), patch.object(projects, "upd", AsyncMock()) as save:
                with pytest.raises(HTTPException) as exc: await projects.patch("journey", projects.ProjectPatch(idea="A different story"), {"id":"tester"})
                assert exc.value.status_code == 409
                save.assert_not_awaited()
        finally: projects._active_audio.discard("journey")
    asyncio.run(run())


@pytest.mark.parametrize("field,value", [("idea", "A child rescues a bird"), ("script", {"scenes": []}), ("style", "cartoon"), ("language", "te"), ("region", "Kerala")])
def test_story_cannot_change_while_images_are_running(field, value):
    async def run():
        p = story(); p["scenes"][0]["status"] = "generating"
        with patch.object(projects, "owned", AsyncMock(return_value=p)), patch.object(projects, "upd", AsyncMock()) as save:
            with pytest.raises(HTTPException) as exc: await projects.patch("journey", projects.ProjectPatch(**{field: value}), {"id":"tester"})
            assert exc.value.status_code == 409
            save.assert_not_awaited()
    asyncio.run(run())


def test_image_concept_edit_survives_reload_and_blocks_old_export():
    async def run():
        m = Memory(story())
        with (patch.object(projects, "db", SimpleNamespace(projects=m)),
              patch.object(projects, "owned", m.find_one), patch.object(projects, "upd", m.upd),
              patch.object(projects, "get_object", AsyncMock(return_value=(b"old", "image/png"))),
              patch.object(projects, "save_media", AsyncMock(return_value="edited.png")),
              patch.object(ai, "gen_image", AsyncMock(return_value=(b"edited", "image/png", False))),
              patch.object(ai, "audit_scene_image", AsyncMock(return_value=[]))):
            assert await projects._scene_job("journey", "tester", "s1", "Add a second bird naturally on the branch")
            reloaded = await m.find_one()
            assert "second bird" in reloaded["scenes"][0]["visual"]
            assert "second bird" in reloaded["script"]["scenes"][0]["visual"]
            assert reloaded["scenes"][1]["image_path"] == "two.png"
            assert reloaded["scenes"][1]["approved"] is False
            assert reloaded["scenes"][1]["continuity_needs_review"] is True
            assert reloaded["scenes"][0]["approved"] is False
            assert reloaded["validation"] is None and reloaded["approved"] is False
            assert reloaded["render"]["status"] == "idle"
            with pytest.raises(HTTPException) as exc: await projects.start_render("journey", {"id":"tester"})
            assert exc.value.status_code == 400
    asyncio.run(run())


@pytest.mark.parametrize("gaps", [[], ["The bird changed color after the edit"]])
def test_later_picture_requires_a_real_continuity_check(gaps):
    async def run():
        m = Memory(story())
        m.p["scenes"][1].update(approved=False, continuity_needs_review=True)
        with (patch.object(projects, "db", SimpleNamespace(projects=m)),
              patch.object(projects, "owned", m.find_one), patch.object(projects, "upd", m.upd),
              patch.object(projects, "get_object", AsyncMock(return_value=(b"image", "image/png"))),
              patch.object(ai, "audit_scene_image", AsyncMock(return_value=gaps)) as audit):
            if gaps:
                with pytest.raises(HTTPException) as exc: await projects.approve_scene("journey", "s2", {"id":"tester"})
                assert exc.value.status_code == 409 and not m.p["scenes"][1]["approved"]
            else:
                await projects.approve_scene("journey", "s2", {"id":"tester"})
                assert m.p["scenes"][1]["approved"] and not m.p["scenes"][1]["continuity_needs_review"]
            audit.assert_awaited_once()
    asyncio.run(run())


@pytest.mark.parametrize("change", [{"narration": "The bird returns with a twig."}, {"visual": "The bird returns with a twig"}])
def test_scene_text_edit_keeps_other_scene_and_requires_fresh_review(change):
    async def run():
        m = Memory(story())
        with patch.object(projects, "db", SimpleNamespace(projects=m)), patch.object(projects, "owned", m.find_one), patch.object(projects, "upd", m.upd):
            await projects.patch_scene("journey", "s1", projects.SceneTextIn(**change), {"id":"tester"})
            assert m.p["scenes"][0]["image_path"] is None
            assert m.p["scenes"][1]["image_path"] == "two.png"
            assert m.p["approved"] is False and m.p["validation"] is None
            assert m.p["render"]["status"] == "idle"
            if "narration" in change: assert m.p["audio"] is None
    asyncio.run(run())


@pytest.mark.parametrize("fault", ["review", "audio", "image", "placeholder", "picture_approval"])
def test_export_cannot_skip_required_gate(fault):
    async def run():
        p = story()
        if fault == "review": p["validation"]["content_fingerprint"] = "old"
        elif fault == "audio": p["audio"] = None
        elif fault == "image": p["scenes"][0]["image_path"] = None
        elif fault == "placeholder": p["scenes"][0]["placeholder"] = True
        else: p["scenes"][0]["approved"] = False
        with patch.object(projects, "owned", AsyncMock(return_value=p)), patch.object(projects, "spawn") as launch:
            with pytest.raises(HTTPException) as exc: await projects.start_render("journey", {"id":"tester"})
            assert exc.value.status_code == 400
            launch.assert_not_called()
    asyncio.run(run())
