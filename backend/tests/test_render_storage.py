"""A completed render must link owned database records to private media objects."""
import asyncio
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import projects


def test_render_saves_captions_and_mp4_for_the_correct_owner():
    project = {
        "id": "story-1", "user_id": "owner-1", "language": "te", "region": "Andhra Pradesh",
        "captions_on": True, "scenes": [{"id": "scene-1", "image_path": "scene.jpg"}],
        "audio": {"path": "voice.mp3", "mode": "ai", "provider": "piper"},
        "render": {"claim_token": "claim-1", "queued_at": "2026-10-16T00:00:00+00:00"},
    }
    find_one = AsyncMock(return_value=project)
    save_media = AsyncMock(side_effect=["private/captions/story.srt", "private/videos/story.mp4"])
    update = AsyncMock()

    def make_clip(_image, _duration, _captions, _lang, output, *_args):
        output.write_bytes(b"clip")

    def make_video(_clips, _audio, output, _work):
        output.write_bytes(b"mp4")

    test_root = Path(__file__).resolve().parents[1]
    assert test_root.is_relative_to(Path(__file__).resolve().parents[2])
    with tempfile.TemporaryDirectory(dir=test_root) as folder:
        audio = Path(folder) / "voice.mp3"
        audio.write_bytes(b"voice")
        with patch.object(projects, "db", SimpleNamespace(projects=SimpleNamespace(find_one=find_one))), \
             patch.object(projects, "CACHE", Path(folder)), \
             patch.object(projects, "cached", new=AsyncMock(return_value=audio)), \
             patch.object(projects, "render_timeline", new=AsyncMock(return_value=(
                 [2.0], [{"start": 0.0, "end": 1.9, "text": "నమస్కారం"}], "estimated"))), \
             patch.object(projects, "save_media", new=save_media), \
             patch.object(projects, "upd", new=update), \
             patch.object(projects, "log_noncritical_event", new=AsyncMock()), \
             patch.object(projects.render, "prep_image"), \
             patch.object(projects.render, "scene_clip", side_effect=make_clip), \
             patch.object(projects.render, "mux", side_effect=make_video), \
             patch.object(projects.render, "duration", return_value=2.0):
            asyncio.run(projects._render_job("story-1", "owner-1"))

    find_one.assert_awaited_once_with({"id": "story-1", "user_id": "owner-1"}, {"_id": 0})
    assert save_media.await_count == 2
    assert save_media.await_args_list[0].args[0:2] == ("owner-1", "captions")
    assert save_media.await_args_list[0].args[3:5] == ("srt", "application/x-subrip")
    assert save_media.await_args_list[1].args[0:2] == ("owner-1", "videos")
    assert save_media.await_args_list[1].args[3:5] == ("mp4", "video/mp4")
    final = update.await_args_list[-1].kwargs["render"]
    assert final["status"] == "done"
    assert final["video_path"] == "private/videos/story.mp4"
    assert final["caption_path"] == "private/captions/story.srt"
