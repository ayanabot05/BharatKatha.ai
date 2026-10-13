"""Adversarial regressions: verify failures that happy-path language checks missed."""
import asyncio
import io
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException, UploadFile

import ai
import projects
import ram_ai
import render
from test_language_quality import SAMPLES


@pytest.mark.parametrize("language", SAMPLES)
def test_one_wrong_script_scene_is_not_hidden_by_the_other_scenes(language):
    scenes = [{"narration": SAMPLES[language]} for _ in range(5)]
    scenes[3] = {"narration": SAMPLES["en" if language != "en" else "te"]}
    passed, detail = ram_ai.check_scene_languages(scenes, language)
    assert not passed
    assert "Scene 4" in detail


def test_combining_marks_do_not_count_as_extra_native_letters():
    # Five Telugu letters and five vowel marks cannot outweigh nine Latin letters.
    assert not ram_ai.check_native_script("కీ కీ కీ కీ కీ abcdefghi", "te")[0]
    assert not ram_ai.check_native_script("hello world అక్షరాలు అక్షరాలు", "en")[0]


def test_script_check_allows_short_brand_name_without_claiming_language_verification():
    passed, detail = ram_ai.check_native_script(SAMPLES["te"] + " AYANA", "te")
    assert passed and "fluency still need review" in detail


@pytest.mark.parametrize("punctuation", ["۔", "؟", "!", "."])
def test_urdu_native_punctuation_does_not_hide_duplicate_sentence(punctuation):
    text = f"{SAMPLES['ur']}{punctuation} {SAMPLES['ur']}{punctuation}"
    assert not ram_ai.check_repeated_narration([{"narration": text}])[0]


def test_word_timestamps_preserve_a_long_spoken_pause():
    words = [{"text": "Wait", "start": .2, "end": .5},
             {"text": "now", "start": 2.0, "end": 2.5}]
    caps = render.timed_captions(words, 3)
    assert caps == words
    assert not any(c["start"] <= 1 <= c["end"] for c in caps)


def test_bengali_zero_duration_onset_keeps_the_first_spoken_word():
    words = [{"text": "দুই", "start": .225, "end": .225},
             {"text": "প্রতিবেশী", "start": .425, "end": .975}]
    assert render.timed_captions(words, 3) == [
        {"text": "দুই প্রতিবেশী", "start": .225, "end": .975}]


@pytest.mark.parametrize("caps", [[], [{"text": "x", "start": float("nan"), "end": 1}],
    [{"text": "x", "start": 2, "end": 1}], [{"text": "x", "start": 0, "end": 8}],
    [{"text": "x", "start": 0, "end": 2}, {"text": "y", "start": 1, "end": 3}]])
def test_invalid_subtitle_timing_is_rejected(caps):
    with pytest.raises(ValueError):
        render.checked_captions(caps, 3)


def test_frame_rounding_does_not_cut_off_the_end_of_narration():
    durations = [1.019] * 12
    actual = render.frame_durations(durations)
    assert sum(actual) >= sum(durations)
    assert sum(actual) - sum(durations) < 1 / render.FPS
    for end in range(1, 13):
        assert 0 <= sum(actual[:end]) - sum(durations[:end]) < 1 / render.FPS


def upload_project(captions=True):
    return {"language": "en", "captions_on": captions, "audio": {"mode": "upload", "duration": 3},
            "scenes": [{"narration": "This script is not what the recording says"}]}


@pytest.mark.parametrize("response", [None, [], [{"text": "bad", "start": 2, "end": 1}]])
def test_failed_transcription_never_substitutes_the_script(response):
    async def check():
        with patch.object(ai, "transcribe", new=AsyncMock(return_value=response)):
            with pytest.raises(RuntimeError, match="turn off burn-in captions"):
                await projects.render_timeline(upload_project(), "recording.mp3")
    asyncio.run(check())


def test_no_captions_means_no_transcription_dependency_or_fake_srt():
    async def check():
        with patch.object(ai, "transcribe", new=AsyncMock(side_effect=RuntimeError("offline"))) as transcribe:
            durations, caps, source = await projects.render_timeline(upload_project(False), "recording.mp3")
            transcribe.assert_not_awaited()
            assert sum(durations) == 3 and caps == [] and source == "none"
    asyncio.run(check())


def test_ai_timeline_keeps_provider_pause_and_marks_source():
    async def check():
        p = {"language": "en", "audio": {"mode": "ai", "duration": 3},
             "scenes": [{"narration": "Wait now", "audio_duration": 3,
                         "audio_captions": [{"text": "Wait", "start": .2, "end": .5},
                                            {"text": "now", "start": 2, "end": 2.5}]}]}
        durations, caps, source = await projects.render_timeline(p, "audio.mp3")
        assert caps[1]["start"] == 2 and source == "provider" and sum(durations) == 3
    asyncio.run(check())


@pytest.mark.parametrize("key,value", [("idea", "Different ending"), ("language", "te"),
                                      ("region", "Kerala"), ("duration", 60), ("script", {"scenes": []})])
def test_review_cannot_approve_content_changed_during_ai_request(key, value):
    p = {"idea": "Water repair", "language": "en", "region": "Andhra Pradesh", "duration": 30,
         "script": {"scenes": [{"narration": "Close the valve"}]}}
    p["validation"] = {"safe": True, "all_passed": True,
                       "content_fingerprint": projects.review_fingerprint(p)}
    assert projects.review_is_current(p)
    p[key] = value
    assert not projects.review_is_current(p)
    async def check():
        with patch.object(projects, "owned", new=AsyncMock(return_value=p)), \
             patch.object(projects, "upd", new=AsyncMock()) as update:
            with pytest.raises(HTTPException, match="older script or idea"):
                await projects.approve("p", {"id": "u"})
            update.assert_not_awaited()
    asyncio.run(check())


@pytest.mark.parametrize("key,value", [("idea", "Different ending"), ("language", "te"), ("region", "Kerala")])
def test_story_context_edit_invalidates_review_audio_and_render(key, value):
    async def check():
        p = {"idea": "Repair", "language": "en", "region": "Andhra Pradesh", "scenes": [],
             "validation": {"all_passed": True}, "approved": True, "render": {"status": "done"}}
        with patch.object(projects, "owned", new=AsyncMock(return_value=p)), \
             patch.object(projects, "upd", new=AsyncMock()) as update:
            await projects.patch("p", projects.ProjectPatch(**{key: value}), {"id": "u"})
            fields = update.call_args.kwargs
            assert fields["validation"] is None and fields["audio"] is None
            assert fields["approved"] is False and fields["render"]["status"] == "idle"
    asyncio.run(check())


def test_audio_upload_invalidates_old_export_and_returns_updated_project():
    async def check():
        p = {"step": 6, "render": {"status": "done", "video_path": "old.mp4"}}
        with patch.object(projects, "owned", new=AsyncMock(return_value=p)), \
             patch.object(projects, "upd", new=AsyncMock()) as update, \
             patch.object(projects, "save_media", new=AsyncMock(return_value="new.mp3")), \
             patch.object(render, "to_mp3_bytes", return_value=b"audio"), \
             patch.object(render, "duration_bytes", return_value=3):
            response = await projects.audio_upload("p", UploadFile(file=io.BytesIO(b"input"), filename="a.wav"), "upload", {"id": "u"})
            assert response is p
            assert update.call_args.kwargs["render"]["status"] == "idle"
            assert update.call_args.kwargs["srt"] is None
    asyncio.run(check())


def concept_review():
    return {"aligned": True, "misses": [], "requirements": [{"source": "repair the pipe", "status": "met",
        "evidence": [{"scene": 1, "field": "visual", "quote": "tightens the coupling"}]}]}


def test_concept_review_accepts_actual_requirement_and_scene_quotes():
    review = concept_review()
    ai.validate_concept_evidence(review, {"scenes": [{"visual": "The worker tightens the coupling."}]}, "Show a worker repair the pipe.")
    assert review["aligned"]


@pytest.mark.parametrize("mutation", ["source", "quote", "scene", "missing_evidence"])
def test_concept_review_rejects_invented_evidence(mutation):
    review = concept_review()
    requirement = review["requirements"][0]
    if mutation == "source":
        requirement["source"] = "A flying tractor"
    elif mutation == "missing_evidence":
        requirement["evidence"] = []
    else:
        requirement["evidence"][0][mutation] = "Invented action" if mutation == "quote" else 9
    with pytest.raises(RuntimeError):
        ai.validate_concept_evidence(review, {"scenes": [{"visual": "The worker tightens the coupling."}]}, "Show a worker repair the pipe.")


def test_missing_requirement_overrides_optimistic_alignment_boolean():
    review = concept_review()
    review["requirements"][0].update(status="missing", evidence=[])
    ai.validate_concept_evidence(review, {"scenes": []}, "Show a worker repair the pipe.")
    assert not review["aligned"] and "repair the pipe" in review["misses"]
