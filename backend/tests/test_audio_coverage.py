"""All creator languages enter the same audio evaluation pipeline."""
import json
import re
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

import ai
import audio_coverage
import audio_eval_corpus
import benchmark_piper_audio
import piper_tts
import server


def test_audio_corpus_matches_backend_and_frontend_languages():
    source = (Path(__file__).resolve().parents[2] / "frontend/src/constants/studio.js").read_text(encoding="utf-8")
    choices = source.split("export const LANGUAGES = [", 1)[1].split("export const TONES", 1)[0]
    frontend = set(re.findall(r'\{ id: "([a-z]{2})", label:', choices))
    expected = set(audio_eval_corpus.ALL_LANGUAGES)
    assert len(expected) == 11
    assert expected == set(ai.LANGS) == frontend
    assert set(audio_eval_corpus.PRIMARY_LANGUAGES) == {"te", "hi", "ta", "mr"}
    assert set(benchmark_piper_audio.SCRIPTS) == expected
    for language in expected:
        assert set(audio_eval_corpus.SCRIPTS[language]) == set(audio_eval_corpus.CASES)
        assert all(audio_eval_corpus.SCRIPTS[language].values())


def test_unrun_languages_are_visible_and_unaccepted():
    rows = audio_coverage.coverage(Path("absent-audio-reports"))
    assert len(rows["languages"]) == 11
    assert not rows["primary_cohort_sample_complete"]
    assert not rows["all_language_sample_complete"]
    assert {row["requested_completion_target_pct"] for row in rows["languages"] if row["priority"] == "primary"} == {100}
    assert {row["requested_completion_target_pct"] for row in rows["languages"] if row["priority"] == "secondary"} == {90}
    assert all(row["stage"] == "corpus_ready" and row["native_speaker_review"] == "pending" for row in rows["languages"])


def test_piper_manifest_rejects_language_not_in_app():
    voice = {"url": "http://127.0.0.1:5000", "model_id": "test", "model_revision": "sha256:123",
             "license_url": "https://example.invalid/license", "license_status": "verified-commercial",
             "hardware_requirements": "CPU"}
    with patch.dict("os.environ", {"PIPER_VOICES_JSON": json.dumps({"xx": voice})}):
        with pytest.raises(RuntimeError, match="not offered by the app"):
            piper_tts.voices()


def test_all_language_voice_manifest_can_be_exposed_to_studio():
    voice = {"url": "http://127.0.0.1:5000", "model_id": "test", "model_revision": "sha256:123",
             "license_url": "https://example.invalid/license", "license_status": "verified-commercial",
             "hardware_requirements": "CPU"}
    manifest = {language: voice for language in audio_eval_corpus.ALL_LANGUAGES}
    with patch.dict("os.environ", {"PIPER_VOICES_JSON": json.dumps(manifest)}):
        assert set(piper_tts.voices()) == set(audio_eval_corpus.ALL_LANGUAGES)
        with pytest.raises(StopIteration) as finished:
            server.meta().send(None)
    piper = next(item for item in finished.value.value["voice_providers"] if item["id"] == "piper")
    assert set(piper["languages"]) == set(audio_eval_corpus.ALL_LANGUAGES)


def test_every_language_fails_closed_without_a_reviewed_open_voice():
    with patch.dict("os.environ", {"PIPER_VOICES_JSON": "{}"}):
        for language in audio_eval_corpus.ALL_LANGUAGES:
            with pytest.raises(RuntimeError, match=f"configured for {language}"):
                benchmark_piper_audio.benchmark(language, Path("unused-audio-output")).send(None)


def test_every_language_routes_explicit_open_speech_without_paid_fallback():
    async def check():
        result = {"audio": b"mock-audio", "words": [], "timing_source": "estimated"}
        with patch.object(piper_tts, "synthesize", new=AsyncMock(return_value=result)) as open_speech, \
             patch.object(ai, "_google_chirp_speech") as chirp, \
             patch.object(ai, "_edge_speech", new=AsyncMock()) as edge:
            for language in audio_eval_corpus.ALL_LANGUAGES:
                script = audio_eval_corpus.SCRIPTS[language]["short"]
                assert await ai.tts_timed(script, "coral", 1.0, language, provider="piper") == result
                open_speech.assert_awaited_with(script, 1.0, language)
            assert open_speech.await_count == len(audio_eval_corpus.ALL_LANGUAGES)
            chirp.assert_not_called()
            edge.assert_not_awaited()
    with pytest.raises(StopIteration):
        check().send(None)
