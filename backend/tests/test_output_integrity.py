"""Adversarial regressions: verify failures that happy-path language checks missed."""
import asyncio
import base64
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


def test_ai_narration_uses_one_synthesis_pass_at_the_chosen_speed():
    async def check():
        from types import SimpleNamespace

        project = {"id": "voice-test", "language": "en", "step": 5, "duration": 30,
                   "render": {"status": "idle"}, "scenes": [
                       {"id": "a", "narration": "First sentence."},
                       {"id": "b", "narration": "Second sentence."}]}
        speech = {"audio": b"mock-mp3", "words": [], "timing_source": "estimated"}
        def concat(_locals, combined):
            combined.write_bytes(b"combined-mp3")

        with (patch.dict("os.environ", {"TTS_PROVIDER": "edge"}),
              patch.object(projects, "owned", new=AsyncMock(return_value=project)),
              patch.object(projects, "upd", new=AsyncMock()) as update,
              patch.object(projects, "save_media", new=AsyncMock(return_value="saved.mp3")),
              patch.object(projects.ai, "tts_timed", new=AsyncMock(return_value=speech)) as tts,
              patch.object(projects.render, "duration", return_value=2.0),
              patch.object(projects.render, "concat_audio", side_effect=concat),
              patch.object(projects, "review_fingerprint", return_value="same")):
            await projects.audio_ai("voice-test", SimpleNamespace(voice="fable", speed=1.0), {"id": "user"})

        assert tts.await_count == 2
        assert all(call.args[2] == 1.0 for call in tts.await_args_list)
        audio = update.await_args.kwargs["audio"]
        assert audio["speed"] == 1.0 and audio["duration_matched"] is False
        assert audio["padded_seconds"] == 0.0

    asyncio.run(check())


def test_managed_voice_uses_recognized_word_times_for_captions():
    async def check():
        from types import SimpleNamespace
        project = {"id": "voice-timing", "language": "en", "step": 5,
                   "render": {"status": "idle"}, "captions_on": True,
                   "scenes": [{"id": "a", "narration": "Hello world"}]}
        speech = {"audio": b"mock-mp3", "words": [], "timing_source": "estimated"}
        words = [{"text": "Hello", "start": .1, "end": .6},
                 {"text": "world", "start": .7, "end": 1.5}]
        def concat(_locals, combined):
            combined.write_bytes(b"combined-mp3")
        with (patch.dict("os.environ", {"TTS_PROVIDER": "google_chirp"}),
              patch.object(projects, "owned", new=AsyncMock(return_value=project)),
              patch.object(projects, "upd", new=AsyncMock()) as update,
              patch.object(projects, "save_media", new=AsyncMock(return_value="saved.mp3")),
              patch.object(projects.ai, "tts_timed", new=AsyncMock(return_value=speech)),
              patch.object(projects.ai, "cloud_word_timestamps", new=AsyncMock(return_value=words)) as timing,
              patch.object(projects.render, "duration", return_value=2.0),
              patch.object(projects.render, "concat_audio", side_effect=concat),
              patch.object(projects, "review_fingerprint", return_value="same")):
            await projects.audio_ai("voice-timing", SimpleNamespace(voice="coral", speed=1.0), {"id": "user"})
        timing.assert_awaited_once_with(b"mock-mp3", "en", "Hello world")
        scene = update.await_args.kwargs["scenes"][0]
        assert scene["caption_timing"] == "cloud_stt"
        assert scene["audio_captions"][0]["start"] == .1
    asyncio.run(check())


def test_cloud_word_timing_rejects_mismatched_speech():
    class Response:
        ok = True
        status_code = 200
        def json(self):
            return {"results": [{"alternatives": [{"words": [
                {"word": "wrong", "startOffset": "0.1s", "endOffset": "0.5s"}]}]}]}
    with (patch.dict("os.environ", {"GOOGLE_CLOUD_PROJECT": "ayana-video-studio"}),
          patch("google.auth.default", return_value=(object(), "ayana-video-studio")),
          patch("google.auth.transport.requests.AuthorizedSession") as session):
        session.return_value.post.return_value = Response()
        with pytest.raises(RuntimeError, match="did not match"):
            ai._cloud_word_timestamps(b"mock-mp3", "en", "Hello world")
        url = session.return_value.post.call_args.args[0]
        assert "/v2/projects/ayana-video-studio/locations/global/recognizers/_:recognize" in url


def test_google_cloud_voice_uses_selected_language_speaker_and_speed():
    class Response:
        ok = True
        status_code = 200

        def json(self):
            return {"audioContent": base64.b64encode(b"cloud-mp3").decode()}

    with (patch.dict("os.environ", {"GOOGLE_CLOUD_PROJECT": "ayana-video-studio"}),
          patch("google.auth.default", return_value=(object(), "ayana-video-studio")),
          patch("google.auth.transport.requests.AuthorizedSession") as session):
        session.return_value.post.return_value = Response()
        result = ai._google_chirp_speech("తెలుగు కథ", "coral", 0.9, "te")

    body = session.return_value.post.call_args.kwargs["json"]
    assert body["voice"] == {"languageCode": "te-IN", "name": "te-IN-Chirp3-HD-Kore"}
    assert body["audioConfig"]["speakingRate"] == 0.9
    assert result == {"audio": b"cloud-mp3", "words": [], "timing_source": "estimated"}


def test_cloud_narration_adds_breath_at_sentence_breaks_only():
    assert ai._chirp_input("Dr. Rao found it. He returned it.") == {
        "markup": "Dr. Rao found it. [pause short] He returned it."}
    assert ai._chirp_input("ఒక చిన్నారి పట్టీని ఇచ్చింది.") == {"text": "ఒక చిన్నారి పట్టీని ఇచ్చింది."}


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
    return {"aligned": True, "misses": [], "scene_checks": [{"scene": 1, "aligned": True,
        "narration_quote": "The worker repairs the pipe", "visual_quote": "tightens the coupling", "issue": ""}],
        "requirements": [{"source": "repair the pipe", "status": "met",
        "evidence": [{"scene": 1, "field": "visual", "quote": "tightens the coupling"}]}]}


def test_concept_review_accepts_actual_requirement_and_scene_quotes():
    review = concept_review()
    ai.validate_concept_evidence(review, {"scenes": [{"narration": "The worker repairs the pipe", "visual": "The worker tightens the coupling."}]}, "Show a worker repair the pipe.")
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
        ai.validate_concept_evidence(review, {"scenes": [{"narration": "The worker repairs the pipe", "visual": "The worker tightens the coupling."}]}, "Show a worker repair the pipe.")


def test_missing_requirement_overrides_optimistic_alignment_boolean():
    review = concept_review()
    review["requirements"][0].update(status="missing", evidence=[])
    ai.validate_concept_evidence(review, {"scenes": [{"narration": "The worker repairs the pipe", "visual": "The worker tightens the coupling."}]}, "Show a worker repair the pipe.")
    assert not review["aligned"] and "repair the pipe" in review["misses"]


def test_scene_mismatch_overrides_optimistic_concept_score():
    review = concept_review()
    review["scene_checks"][0].update(aligned=False, issue="Repair appears before the narration reaches it")
    ai.validate_concept_evidence(review, {"scenes": [{"narration": "The worker repairs the pipe", "visual": "The worker tightens the coupling."}]}, "Show a worker repair the pipe.")
    assert not review["aligned"]
    assert "Scene 1: Repair appears before" in review["misses"][0]


def test_is_detail_or_closeup_detection():
    assert ai.is_detail_or_closeup("Extreme close-up of wrench tightening the bolt on the pipe flange")
    assert ai.is_detail_or_closeup("Macro shot of water dripping through the crack")
    assert ai.is_detail_or_closeup("Tight shot focused on hands adjusting the valve")
    assert not ai.is_detail_or_closeup("Wide shot of two farmers standing in a dry field at sunset")
    assert not ai.is_detail_or_closeup("Ranga walks across the village square")


def test_closeup_scene_prompt_enforces_strict_mechanical_continuity():
    project = {
        "region": "Andhra Pradesh",
        "style": "storybook",
        "script": {
            "story": "Repairing a village pipeline.",
            "characters": [{"name": "Ranga", "look": "52-year-old Telugu farmer with grey mustache"}]
        }
    }
    scene = {"visual": "Close-up of wrench tightening the 4-bolt flange coupling."}
    prompt = ai.scene_prompt(project, scene, with_ref=True)
    assert "CONTINUITY REFERENCE" in prompt
    assert "flange shape, bolt count" in prompt
    assert "Primary Character Profile: Ranga: 52-year-old Telugu farmer" in prompt


def test_first_image_prompt_does_not_spoil_later_action():
    project = {"region": "Andhra Pradesh", "style": "cartoon",
               "script": {"story": "Later, they repair the pipe with a wrench.", "characters": []}}
    prompt = ai.scene_prompt(project, {"visual": "A rusty pipe leaks while nobody touches it."}, False)
    assert "Later, they repair" not in prompt
    assert "A rusty pipe leaks while nobody touches it" in prompt
    assert "do not introduce a tool" in prompt


def test_best_scene_reference_prefers_immediate_predecessor_for_closeups():
    project = {
        "script": {"characters": [{"name": "Ranga", "look": "farmer"}, {"name": "Meena", "look": "mechanic"}]},
        "scenes": [
            {"id": "s1", "visual": "Ranga stands by the canal"},
            {"id": "s2", "visual": "Meena brings the wrench"},
            {"id": "s3", "visual": "Meena aligns the pipe joint with 4 bolts"},
            {"id": "s4", "visual": "Extreme close-up of wrench tightening a bolt on the joint"}
        ]
    }
    s1, s2, s3, s4 = project["scenes"]
    refs = [(s1, b"img_1"), (s2, b"img_2"), (s3, b"img_3")]
    # For Scene 4 (close-up of wrench on joint), it must pick the immediate predecessor s3 (where the joint was established),
    # not s2 or s1.
    selected = projects.best_scene_reference(project, s4, refs)
    assert selected == b"img_3"


def test_cloud_caption_alignment_preserves_script_when_speech_recognition_mishears_name():
    words = [{"text": "Grandma", "start": 0.1, "end": 0.4},
             {"text": "shows", "start": 0.5, "end": 0.8},
             {"text": "Pear", "start": 0.9, "end": 1.2},
             {"text": "the", "start": 1.2, "end": 1.35},
             {"text": "kite", "start": 1.4, "end": 1.8}]
    aligned = ai._align_caption_words("Grandma shows Veer the kite.", words)
    assert " ".join(word["text"] for word in aligned) == "Grandma shows Veer the kite."
    assert aligned[2]["start"] == 0.9 and aligned[-1]["end"] == 1.8


def test_cloud_caption_alignment_folds_split_recognition_into_one_script_word():
    words = [{"text": "பாட்டி", "start": 0, "end": 0.3},
             {"text": "தேர்", "start": 0.4, "end": 0.7},
             {"text": "எனக்கு", "start": 0.7, "end": 1.1}]
    aligned = ai._align_caption_words("பாட்டி பேரனுக்குக்", words)
    assert [word["text"] for word in aligned] == ["பாட்டி", "பேரனுக்குக்"]
    assert aligned[-1]["start"] == 0.4 and aligned[-1]["end"] == 1.1


def test_best_scene_reference_preserves_prop_when_characters_enter_later():
    project = {"script": {"characters": [{"name": "Ranga", "look": "farmer"},
                                           {"name": "Meena", "look": "mechanic"}]}}
    pipe = {"visual": "A rusted metal pipe leaks at its joint."}
    people = {"visual": "Ranga and Meena walk through a coconut grove."}
    inspection = {"visual": "Ranga and Meena inspect the damaged pipe joint."}
    assert projects.best_scene_reference(project, inspection,
                                         [(pipe, b"pipe"), (people, b"people")]) == b"pipe"


def test_kite_scene_reuses_reference_with_grandmother_and_child():
    project = {"script": {"characters": []}}
    first = {"visual": "Grandmother and boy hold a torn red kite in the courtyard"}
    closeup = {"visual": "Close-up of boy's hands pressing a patch onto the red kite"}
    later = {"visual": "Grandmother and boy watch the repaired red kite rise"}
    assert projects.best_scene_reference(project, later,
                                         [(first, b"both-characters"), (closeup, b"closeup")]) == b"both-characters"


def test_paused_image_batch_resumes_only_missing_scenes():
    scenes = [{"id": "one", "status": "ready", "image_path": "saved.png", "placeholder": False},
              {"id": "two", "status": "ready", "image_path": "saved2.png", "placeholder": False},
              {"id": "three", "status": "pending", "image_path": None, "placeholder": False},
              {"id": "four", "status": "failed", "image_path": None, "placeholder": False}]
    assert projects.missing_scene_ids(scenes) == ["three", "four"]


def test_image_batch_starts_only_one_queued_scene_at_a_time():
    async def check():
        scenes = [{"id": str(i), "status": "queued", "image_path": None} for i in range(5)]
        project = {"id": "p-serial", "scenes": scenes}
        snapshots = []

        async def mark(_pid, ids, status):
            for scene in scenes:
                if scene["id"] in ids:
                    scene["status"] = status

        async def generate(_pid, _uid, sid, instruction=None, ref=None):
            snapshots.append((sid, [scene["status"] for scene in scenes]))
            await asyncio.sleep(0)
            scenes[int(sid)]["status"] = "ready"
            return b"image", False

        fake_db = type("DB", (), {})()
        fake_db.projects = type("Projects", (), {})()
        fake_db.projects.find_one = AsyncMock(return_value=project)
        fake_db.projects.update_one = AsyncMock()
        with patch.object(projects, "db", fake_db), \
             patch.object(projects, "mark_scene_status", new=mark), \
             patch.object(projects, "_scene_job", new=generate), \
             patch.dict("os.environ", {"IMAGE_SCENE_GAP_SECONDS": "0"}):
            await projects._all_scenes_job("p-serial", "u-serial", [str(i) for i in range(5)])

        assert [sid for sid, _ in snapshots] == [str(i) for i in range(5)]
        for i, (_, statuses) in enumerate(snapshots):
            assert statuses == ["ready"] * i + ["generating"] + ["queued"] * (4 - i)
        assert all(scene["status"] == "ready" for scene in scenes)

    asyncio.run(check())


def test_words_per_second_calibration_and_budget():
    for lang in SAMPLES:
        assert lang in ram_ai.WORDS_PER_SECOND
        assert 1.4 <= ram_ai.WORDS_PER_SECOND[lang] <= 2.2

    # A 30s Telugu script with 52 words should pass cleanly under calibrated pacing
    scenes = [{"narration": "ఒక రెండు మూడు నాలుగు ఐదు ఆరు ఏడు ఎనిమిది తొమ్మిది పది పదకొండు"} for _ in range(5)]
    passed, msg = ram_ai.check_narration_budget(scenes, 30, "te")
    assert passed
    assert "Duration is an estimate" in msg

    too_short = [{"narration": "ఒక రెండు మూడు నాలుగు ఐదు ఆరు"} for _ in range(5)]
    passed, msg = ram_ai.check_narration_budget(too_short, 30, "te")
    assert not passed
    assert "original idea" in msg

    # Timing estimates must not veto a script that satisfies its idea.
    script = {"title": "A pipe repair", "hook": "Why is the pipe leaking?",
              "scenes": [{"narration": "They find the leak", "visual": "Two villagers inspect the leak", "beat": "setup"},
                         {"narration": "They plan a repair", "visual": "They inspect the pipe", "beat": "setup"},
                         {"narration": "They fit a clamp", "visual": "They fit a clamp", "beat": "conflict"},
                         {"narration": "They tighten it", "visual": "They tighten its bolt", "beat": "twist"},
                         {"narration": "The leak stops", "visual": "The pipe is dry", "beat": "ending"}]}
    checks = ram_ai.run_ram_ai_checks(script, "en", 30)
    timing = next(c for c in checks["checks"] if c["check"] == "Narration Length (Advisory)")
    assert timing["advisory"] and not timing["passed"]
    assert checks["all_passed"]


def test_camera_motion_modes():
    frames = 90
    for idx in range(6):
        z, x, y = render.camera_motion(idx, frames)
        assert isinstance(z, str) and len(z) > 0
        assert isinstance(x, str) and len(x) > 0
        assert isinstance(y, str) and len(y) > 0
        if idx == 0:
            assert "1.18" in z  # Hook push-in energy


def test_script_font_config_covers_all_supported_languages():
    for lang in SAMPLES:
        assert lang in render.SCRIPT_FONT_CONFIG
        cfg = render.SCRIPT_FONT_CONFIG[lang]
        assert 40 <= cfg["size"] <= 52
        assert 300 <= cfg["margin"] <= 330  # Safe zone: above bottom platform UI
