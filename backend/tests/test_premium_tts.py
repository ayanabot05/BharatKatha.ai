"""Premium calls require an operator rate, cap and creator budget."""
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

import ai
import premium_tts
import projects
import server


RATES = json.dumps({"google_chirp": {"model_id": "chirp3-hd", "all_in_inr_per_1000_chars": "2.00",
                                     "includes_caption_stt": True}})
ENV = {"TTS_PROVIDER": "google_chirp", "TTS_PREMIUM_RATES_JSON": RATES,
       "TTS_PREMIUM_MAX_REQUEST_INR": "1.00"}


def test_quote_rounds_up_and_requires_all_in_rate():
    with patch.dict("os.environ", ENV):
        estimate = premium_tts.quote("google_chirp", ["Hello", " world"])
        assert estimate["characters"] == 11
        assert estimate["estimated_cost_inr"] == 0.03
        assert estimate["operator_cap_inr"] == 1.0
        assert premium_tts.quote("google_chirp", ["a", "b"])["estimated_cost_inr"] == 0.02
    invalid = json.dumps({"google_chirp": {"model_id": "chirp3-hd", "all_in_inr_per_1000_chars": "2"}})
    with patch.dict("os.environ", {**ENV, "TTS_PREMIUM_RATES_JSON": invalid}):
        with pytest.raises(RuntimeError, match="caption transcription"):
            premium_tts.pricing()


def test_meta_hides_unpriced_premium_voice():
    with patch.dict("os.environ", {"TTS_PROVIDER": "google_chirp",
                                   "TTS_PREMIUM_RATES_JSON": "{}", "TTS_PREMIUM_MAX_REQUEST_INR": ""}):
        try:
            server.meta().send(None)
        except StopIteration as finished:
            data = finished.value
    assert data["default_voice_provider"] == "edge"
    assert next(item for item in data["voice_providers"] if item["id"] == "google_chirp")["languages"] == []


def test_premium_provider_fails_before_network_without_budget_or_rate():
    with patch.dict("os.environ", ENV), patch.object(ai, "_google_chirp_speech") as chirp:
        with pytest.raises(RuntimeError, match="maximum INR budget"):
            ai.tts_timed("Hello", "coral", 1, "en", provider="google_chirp").send(None)
        with pytest.raises(RuntimeError, match="exceeds the permitted budget"):
            ai.tts_timed("Hello", "coral", 1, "en", provider="google_chirp", max_cost_inr=0.001).send(None)
        with pytest.raises(RuntimeError, match="operator request cap"):
            ai.tts_timed("Hello", "coral", 1, "en", provider="google_chirp", max_cost_inr=2).send(None)
        chirp.assert_not_called()
    with patch.dict("os.environ", {"TTS_PROVIDER": "google_chirp", "TTS_PREMIUM_RATES_JSON": "{}",
                                       "TTS_PREMIUM_MAX_REQUEST_INR": ""}), patch.object(ai, "_google_chirp_speech") as chirp:
        with pytest.raises(RuntimeError, match="not configured"):
            ai.tts_timed("Hello", "coral", 1, "en", provider="google_chirp", max_cost_inr=1).send(None)
        chirp.assert_not_called()


def test_preview_checks_budget_before_speech():
    body = server.PreviewIn(text="Hello", provider="google_chirp")
    with patch.dict("os.environ", ENV), patch.object(server.ai, "tts", new=AsyncMock()) as speech:
        with pytest.raises(HTTPException) as error:
            server.voice_preview(body, {"id": "user"}).send(None)
        assert error.value.status_code == 400
        speech.assert_not_awaited()


def test_project_checks_total_budget_before_speech_or_asset_write():
    project = {"id": "premium-budget", "scenes": [{"narration": "Hello"}, {"narration": "World"}],
               "render": {"status": "idle"}}
    body = SimpleNamespace(voice="coral", speed=1.0, provider="google_chirp", max_cost_inr=0.01)
    with patch.dict("os.environ", ENV), patch.object(projects, "owned", new=AsyncMock(return_value=project)), \
         patch.object(projects.ai, "tts_timed", new=AsyncMock()) as speech, \
         patch.object(projects, "save_media", new=AsyncMock()) as save:
        with pytest.raises(HTTPException) as error:
            projects._audio_ai("premium-budget", body, {"id": "user"}).send(None)
        assert error.value.status_code == 400
        speech.assert_not_awaited()
        save.assert_not_awaited()
