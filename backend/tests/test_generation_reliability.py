import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
import ai
import projects
import generation_reliability as reliability


def test_temporary_error_retries_but_auth_does_not():
    async def run():
        with patch.object(reliability.asyncio, "sleep", AsyncMock()):
            operation = AsyncMock(side_effect=[TimeoutError(), b"ok"])
            assert await reliability.retry_transient(operation, "test") == b"ok"
            assert operation.await_count == 2
            operation = AsyncMock(side_effect=RuntimeError("reauthentication needed"))
            with pytest.raises(RuntimeError):
                await reliability.retry_transient(operation, "test")
            assert operation.await_count == 1
            operation = AsyncMock(side_effect=TimeoutError())
            with pytest.raises(TimeoutError):
                await reliability.retry_transient(operation, "test")
            assert operation.await_count == 3
    asyncio.run(run())


def test_review_timeout_does_not_regenerate_the_image():
    async def run():
        scene = {"id": "s1", "visual": "A bird on a branch", "narration": "A bird rests."}
        collection = SimpleNamespace(find_one=AsyncMock(return_value={"scenes": [scene]}), update_one=AsyncMock())
        with (patch.object(projects, "db", SimpleNamespace(projects=collection)),
              patch.object(projects, "save_media", AsyncMock(return_value="saved.png")),
              patch.object(ai, "gen_image", AsyncMock(return_value=(b"image", "image/png", False))) as generate,
              patch.object(ai, "audit_scene_image", AsyncMock(side_effect=[TimeoutError(), []])),
              patch.object(reliability.asyncio, "sleep", AsyncMock())):
            assert await projects._scene_job("p", "u", "s1") == (b"image", False)
            assert generate.await_count == 1
    asyncio.run(run())


def test_retry_reuses_picture_saved_when_review_service_failed():
    from test_edit_journey import Memory

    async def run():
        memory = Memory({"scenes": [{"id": "s1", "visual": "A bird", "narration": "A bird rests."}]})
        with (patch.object(projects, "db", SimpleNamespace(projects=memory)),
              patch.object(projects, "save_media", AsyncMock(return_value="candidate.png")),
              patch.object(projects, "get_object", AsyncMock(return_value=(b"image", "image/png"))),
              patch.object(ai, "gen_image", AsyncMock(return_value=(b"image", "image/png", False))) as generate,
              patch.object(ai, "audit_scene_image", AsyncMock(side_effect=[RuntimeError("reauthentication needed"), []]))):
            with pytest.raises(projects.ImageServiceError):
                await projects._scene_job("p", "u", "s1")
            assert memory.p["scenes"][0]["image_candidate"]["path"] == "candidate.png"
            assert memory.p["scenes"][0]["status"] == "failed"
            assert await projects._scene_job("p", "u", "s1") == (b"image", False)
            assert generate.await_count == 1
            assert memory.p["scenes"][0]["image_candidate"] is None
    asyncio.run(run())


@pytest.mark.parametrize("failure,expected_calls", [(None, 3), (projects.ImageServiceError("Reconnect provider"), 1)])
def test_batch_continues_after_scene_failure_but_pauses_for_provider_failure(failure, expected_calls):
    async def run():
        scenes = [{"id": str(i), "status": "queued"} for i in range(3)]
        collection = SimpleNamespace(find_one=AsyncMock(return_value={"scenes": scenes}), update_one=AsyncMock())
        generate = AsyncMock(side_effect=[failure, (b"two", False), (b"three", False)])
        with (patch.object(projects, "db", SimpleNamespace(projects=collection)),
              patch.object(projects, "mark_scene_status", AsyncMock()),
              patch.object(projects, "_scene_job", generate),
              patch.dict("os.environ", {"IMAGE_SCENE_GAP_SECONDS": "0"})):
            await projects._all_scenes_job("p", "u", ["0", "1", "2"])
            assert generate.await_count == expected_calls
            assert "p" not in projects._active_generations
            if failure:
                assert any(call.args[1]["$set"].get("scenes.$.error") == "Reconnect provider"
                           for call in collection.update_one.await_args_list)
    asyncio.run(run())


def test_audio_failure_identifies_stage_without_exposing_provider_details():
    async def run():
        project = {"scenes": [{"narration": "Hello"}], "language": "en"}
        with (patch.dict("os.environ", {"TTS_PROVIDER": "edge"}),
              patch.object(projects, "owned", AsyncMock(return_value=project)),
              patch.object(ai, "tts_timed", AsyncMock(side_effect=RuntimeError("invalid_grant secret provider detail")))):
            with pytest.raises(projects.HTTPException) as error:
                await projects.audio_ai("p", projects.VoiceIn(), {"id": "u"})
            assert error.value.status_code == 502
            assert error.value.detail["code"] == "generation_failed"
            assert "Voice generation" in error.value.detail["message"]
            assert "secret" not in error.value.detail["message"]
            assert "p" not in projects._active_audio
    asyncio.run(run())


def test_caption_mismatch_preserves_voice_and_retry_reuses_it():
    from test_edit_journey import Memory

    async def run():
        memory = Memory({"id": "p", "language": "te", "step": 5, "captions_on": True,
                         "scenes": [{"id": "s1", "narration": "అమ్మ వచ్చింది"}]})
        words = [{"text": "అమ్మ", "start": 0.1, "end": 0.8}, {"text": "వచ్చింది", "start": 0.9, "end": 1.7}]
        def concat(paths, destination):
            destination.write_bytes(b"combined")
        with (patch.dict("os.environ", {"TTS_PROVIDER": "google_chirp",
                                         "TTS_PREMIUM_RATES_JSON": '{"google_chirp":{"model_id":"chirp3-hd","all_in_inr_per_1000_chars":"2","includes_caption_stt":true}}',
                                         "TTS_PREMIUM_MAX_REQUEST_INR": "1"}),
              patch.object(projects, "owned", memory.find_one), patch.object(projects, "upd", memory.upd),
              patch.object(projects, "save_media", AsyncMock(return_value="voice.mp3")),
              patch.object(projects, "get_object", AsyncMock(return_value=(b"audio", "audio/mpeg"))),
              patch.object(projects, "review_fingerprint", return_value="same"),
              patch.object(projects.render, "duration", return_value=2.0),
              patch.object(projects.render, "concat_audio", side_effect=concat),
              patch.object(ai, "tts_timed", AsyncMock(return_value={"audio": b"audio", "words": [], "timing_source": "estimated"})) as voice,
              patch.object(ai, "cloud_word_timestamps", AsyncMock(side_effect=[RuntimeError("Cloud speech recognition did not match the narration closely enough for timed captions"), words]))):
            paid_voice = projects.VoiceIn(provider="google_chirp", max_cost_inr=0.10)
            first = await projects.audio_ai("p", paid_voice, {"id": "u"})
            assert first["audio"]["path"] == "voice.mp3"
            assert first["audio"]["caption_status"] == "failed"
            assert first["scenes"][0]["audio_captions"] == []
            assert first["captions_on"] is True
            second = await projects.audio_ai("p", paid_voice, {"id": "u"})
            assert second["audio"]["caption_status"] == "ready"
            assert second["scenes"][0]["audio_captions"]
            assert voice.await_count == 1
            # An actual narration change must invalidate the reused voice.
            memory.p["scenes"][0]["narration"] = "నాన్న వచ్చారు"
            memory.p["captions_on"] = False
            await projects.audio_ai("p", paid_voice, {"id": "u"})
            assert voice.await_count == 2
    asyncio.run(run())
