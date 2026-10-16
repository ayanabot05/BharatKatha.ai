"""Routing and protocol checks; these do not prove a live Piper voice works."""
import asyncio
from unittest.mock import AsyncMock, patch

import httpx
import pytest

import ai
import benchmark_piper_audio
import piper_tts
import projects
import server

VOICE = {"url": "http://127.0.0.1:5000", "model_id": "voice-test", "model_revision": "sha256:1234",
         "license_url": "https://example.invalid/license", "license_status": "verified-commercial",
         "hardware_requirements": "2 CPU, 1 GiB RAM"}


def test_unaligned_open_speech_is_marked_estimated_not_verified():
    assert projects.audio_caption_status([{"audio_words": [], "caption_timing": "estimated"}]) == "estimated"
    assert projects.audio_caption_status([{"audio_words": [{"text": "Hello"}]}]) == "ready"
    assert projects.audio_caption_status([{"caption_error": "alignment failed"}]) == "failed"
    assert projects.audio_caption_status([{"audio_words": []}], captions_on=False) == "ready"


def test_piper_endpoint_configuration_is_language_scoped():
    import json
    with patch.dict("os.environ", {"PIPER_VOICES_JSON": json.dumps({"te": {**VOICE, "url": VOICE["url"] + "/"}})}):
        assert piper_tts.voices()["te"]["url"] == "http://127.0.0.1:5000"
        assert piper_tts.model_signature("te") == "voice-test@sha256:1234"
    with patch.dict("os.environ", {"PIPER_VOICES_JSON": "[]"}):
        with pytest.raises(RuntimeError, match="language-to-voice"):
            piper_tts.voices()


def test_piper_rejects_noncommercial_voice():
    import json
    with patch.dict("os.environ", {"PIPER_VOICES_JSON": json.dumps({"hi": {**VOICE, "license_status": "noncommercial"}})}):
        with pytest.raises(RuntimeError, match="no verified commercial license"):
            piper_tts.voices()


def test_meta_hides_piper_when_voice_license_is_unverified():
    import json
    with patch.dict("os.environ", {"PIPER_VOICES_JSON": json.dumps({"hi": {**VOICE, "license_status": "noncommercial"}})}):
        result = asyncio.run(server.meta())
    piper = next(item for item in result["voice_providers"] if item["id"] == "piper")
    assert piper["languages"] == []


def test_benchmark_refuses_to_run_without_reviewed_voice(tmp_path):
    with patch.dict("os.environ", {"PIPER_VOICES_JSON": "{}"}):
        with pytest.raises(RuntimeError, match="No commercially reviewed Piper voice"):
            asyncio.run(benchmark_piper_audio.benchmark("te", tmp_path / "audio"))
    assert not (tmp_path / "audio").exists()


def test_piper_requires_configured_language_and_never_calls_premium():
    with patch.dict("os.environ", {"PIPER_VOICES_JSON": "{}", "TTS_PROVIDER": "edge"}), \
         patch.object(ai, "_google_chirp_speech") as chirp, \
         patch.object(ai, "_edge_speech", new=AsyncMock()) as edge:
        with pytest.raises(RuntimeError, match="not configured for language te"):
            ai.tts_timed("నమస్కారం", "coral", 1, "te", provider="piper").send(None)
        chirp.assert_not_called()
        edge.assert_not_awaited()


def test_premium_provider_requires_operator_configuration():
    with patch.dict("os.environ", {"TTS_PROVIDER": "edge"}), \
         patch.object(ai, "_google_chirp_speech") as chirp:
        with pytest.raises(RuntimeError, match="not enabled by the operator"):
            ai.tts_timed("Hello", "coral", 1, "en", provider="google_chirp").send(None)
        chirp.assert_not_called()


def test_configured_premium_provider_still_requires_request_selection():
    with patch.dict("os.environ", {"TTS_PROVIDER": "google_chirp"}), \
         patch.object(ai, "_google_chirp_speech") as chirp:
        with pytest.raises(RuntimeError, match="explicitly"):
            ai.tts_timed("Hello", "coral", 1, "en").send(None)
        chirp.assert_not_called()


def test_explicit_configured_premium_route_remains_available():
    expected = {"audio": b"mock-mp3", "words": [], "timing_source": "estimated"}
    import json
    rate = json.dumps({"google_chirp": {"model_id": "chirp3-hd", "all_in_inr_per_1000_chars": "2",
                                        "includes_caption_stt": True}})
    with patch.dict("os.environ", {"TTS_PROVIDER": "google_chirp", "TTS_PREMIUM_RATES_JSON": rate,
                                   "TTS_PREMIUM_MAX_REQUEST_INR": "1"}), \
         patch.object(ai.asyncio, "to_thread", new=AsyncMock(return_value=expected)) as call:
        try:
            ai.tts_timed("Hello", "coral", 1, "en", provider="google_chirp", max_cost_inr=0.01).send(None)
        except StopIteration as finished:
            result = finished.value
    assert result == expected
    call.assert_awaited_once_with(ai._google_chirp_speech, "Hello", "coral", 1, "en")


def test_piper_sends_text_and_speed_to_service():
    async def check():
        captured = {}
        def handle(request):
            captured["url"] = str(request.url)
            captured["body"] = request.read().decode()
            return httpx.Response(200, content=b"RIFFfake-wav")
        client = httpx.AsyncClient(transport=httpx.MockTransport(handle))
        import json
        with patch.dict("os.environ", {"PIPER_VOICES_JSON": json.dumps({"hi": VOICE})}), \
             patch.object(piper_tts.httpx, "AsyncClient") as factory, \
             patch("render.to_mp3_bytes", return_value=b"mp3"):
            factory.return_value.__aenter__ = AsyncMock(return_value=client)
            factory.return_value.__aexit__ = AsyncMock(return_value=None)
            result = await piper_tts.synthesize("नमस्ते", 1.25, "hi")
        await client.aclose()
        assert captured["url"] == "http://127.0.0.1:5000/synthesize"
        assert '"length_scale":0.8' in captured["body"].replace(" ", "")
        assert result["audio"] == b"mp3"
        assert result["timing_source"] == "estimated"
        assert result["model_id"] == "voice-test@sha256:1234"
        assert result["synthesis_ms"] >= 0
    asyncio.run(check())


def test_piper_rejects_invalid_audio_without_provider_fallback():
    async def check():
        client = httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(200, content=b"bad")))
        import json
        with patch.dict("os.environ", {"PIPER_VOICES_JSON": json.dumps({"en": VOICE})}), \
             patch.object(piper_tts.httpx, "AsyncClient") as factory:
            factory.return_value.__aenter__ = AsyncMock(return_value=client)
            factory.return_value.__aexit__ = AsyncMock(return_value=None)
            with pytest.raises(RuntimeError, match="invalid WAV"):
                await ai.tts_timed("Hello", "coral", 1, "en", provider="piper")
        await client.aclose()
    asyncio.run(check())


def test_audio_cache_changes_with_piper_model_revision():
    from types import SimpleNamespace

    async def check():
        project = {"id": "piper-cache", "language": "te", "step": 5,
                   "render": {"status": "idle"}, "captions_on": True,
                   "scenes": [{"id": "scene-1", "narration": "తెలుగు కథ"}]}
        speech = {"audio": b"mock-mp3", "words": [], "timing_source": "estimated",
                  "model_id": "voice@revision-1", "synthesis_ms": 42}
        def concat(_locals, combined):
            combined.write_bytes(b"combined-mp3")
        body = SimpleNamespace(voice="coral", speed=1.0, provider="piper")
        with patch.object(projects, "owned", new=AsyncMock(return_value=project)), \
             patch.object(projects, "upd", new=AsyncMock()) as update, \
             patch.object(projects, "save_media", new=AsyncMock(return_value="saved.mp3")), \
             patch.object(projects.ai, "tts_timed", new=AsyncMock(return_value=speech)) as tts, \
             patch.object(projects.render, "duration", return_value=2.0), \
             patch.object(projects.render, "concat_audio", side_effect=concat), \
             patch.object(projects, "review_fingerprint", return_value="same"), \
             patch.object(piper_tts, "model_signature", side_effect=["voice@revision-1"] * 2 + ["voice@revision-2"] * 2):
            await projects.audio_ai("piper-cache", body, {"id": "user"})
            first_key = project["scenes"][0]["audio_source_key"]
            assert update.await_args.kwargs["audio"]["caption_status"] == "estimated"
            assert update.await_args.kwargs["scenes"][0]["audio_model_id"] == "voice@revision-1"
            assert update.await_args.kwargs["scenes"][0]["audio_synthesis_ms"] == 42
            await projects.audio_ai("piper-cache", body, {"id": "user"})
            assert tts.await_count == 2
            assert project["scenes"][0]["audio_source_key"] != first_key
    asyncio.run(check())
