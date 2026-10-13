"""Offline quality gates for every language exposed by the studio."""
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

import ai
import ram_ai
import render


SAMPLES = {
    "hi": "गाँव के दो पड़ोसी मिलकर पानी बचाते हैं",
    "bn": "দুই প্রতিবেশী মিলে গ্রামের জল বাঁচায়",
    "mr": "दोन शेजारी मिळून गावचे पाणी वाचवतात",
    "te": "ఇద్దరు పొరుగువారు కలిసి ఊరి నీటిని కాపాడారు",
    "ta": "இரு அண்டை வீட்டார் சேர்ந்து ஊரின் நீரை காப்பாற்றினர்",
    "gu": "બે પડોશીઓ મળીને ગામનું પાણી બચાવે છે",
    "ur": "دو پڑوسی مل کر گاؤں کا پانی بچاتے ہیں",
    "kn": "ಇಬ್ಬರು ನೆರೆಹೊರೆಯವರು ಸೇರಿ ಊರಿನ ನೀರು ಉಳಿಸಿದರು",
    "or": "ଦୁଇ ପଡ଼ୋଶୀ ମିଶି ଗାଁର ପାଣି ବଞ୍ଚାଇଲେ",
    "ml": "രണ്ട് അയൽക്കാർ ചേർന്ന് ഗ്രാമത്തിലെ വെള്ളം സംരക്ഷിച്ചു",
    "en": "Two neighbours save their village water together",
}


@pytest.mark.parametrize("language", SAMPLES)
def test_language_has_script_font_and_caption(language):
    assert language in ai.LANGS
    assert language in render.FONT_BY_LANG
    assert (render.FONTS / render.FONT_BY_LANG[language]).is_file()
    assert ram_ai.check_native_script(SAMPLES[language], language)[0]
    assert not ram_ai.check_native_script("", language)[0]
    if language != "en":
        assert not ram_ai.check_native_script("Two neighbours save water", language)[0]
    else:
        assert not ram_ai.check_native_script(SAMPLES["te"], language)[0]
    # The export path burns ASS captions through FFmpeg/libass.
    with TemporaryDirectory(dir=Path(__file__).parent) as directory:
        target = Path(directory) / "caption.ass"
        render.caption_ass([{"text": SAMPLES[language], "start": 0, "end": 3}], language, target)
        contents = target.read_text(encoding="utf-8")
        assert SAMPLES[language] in contents
        family = render.font_family(language)
        assert family in contents


@pytest.mark.parametrize("language", SAMPLES)
def test_voice_route_is_explicit(language):
    if language == "or":
        assert language not in ai.EDGE_VOICES
    else:
        female, male = ai.EDGE_VOICES[language]
        assert female != male and female.endswith("Neural") and male.endswith("Neural")


def test_unmapped_region_and_language_do_not_default_to_other_culture():
    assert "Telangana" not in ram_ai.get_region_aesthetic_note("Assam")
    assert ram_ai.get_regional_hooks("gu") == []
    assert ram_ai.get_regional_hooks("ur") == []
    assert ram_ai.get_regional_hooks("or") == []


def test_incomplete_scene_cannot_pass_review_checks():
    scenes = [{"narration": "A clear short story sentence", "visual": "one clear shot", "beat": "setup"}
              for _ in range(5)]
    scenes[-1] = {"narration": "", "visual": "", "beat": "ending"}
    result = ram_ai.run_ram_ai_checks({"title": "Story", "scenes": scenes}, "en", 30)
    assert not result["all_passed"]
    assert any(c["check"] == "Complete Scene Directions" and not c["passed"] for c in result["checks"])
    assert not ram_ai.check_ending_beat(scenes)[0]


def test_image_prompt_prioritizes_current_story_state_over_region_scenery():
    project = {"region": "Andhra Pradesh", "style": "storybook",
               "script": {"story": "The village suffers a drought before repairing the canal.", "characters": []}}
    prompt = ai.scene_prompt(project, {"visual": "A dry cracked field with no green crops."}, False)
    assert "dry cracked field" in prompt
    assert "Lush Godavari" not in prompt
    assert "override generic regional cues" in prompt
    assert "Never show a later repaired or prosperous outcome early" in prompt


def test_scene_references_follow_character_after_first_appearance():
    import projects

    project = {"script": {"characters": [{"name": "Ranga", "look": "farmer"},
                                          {"name": "Meena", "look": "repair worker"}]},
               "scenes": [{"id": "one", "visual": "Ranga waits by the pipe"},
                          {"id": "two", "visual": "Meena inspects the pipe"},
                          {"id": "three", "visual": "Meena tightens the coupling"}]}

    one, two, three = project["scenes"]
    assert projects.best_scene_reference(project, two, [(one, b"one")]) == b"one"
    assert projects.best_scene_reference(project, three, [(one, b"one"), (two, b"two")]) == b"two"


@pytest.mark.parametrize("language", SAMPLES)
def test_repeated_spoken_line_is_caught_in_every_language(language):
    line = SAMPLES[language]
    scenes = [{"narration": line, "visual": "one distinct shot", "beat": "setup"}
              for _ in range(5)]
    scenes[1]["narration"] = line + "!"
    result = ram_ai.run_ram_ai_checks({"title": "Story", "scenes": scenes}, language, 60)
    repeated = next(c for c in result["checks"] if c["check"] == "No Repeated Narration")
    assert not repeated["passed"]
    assert "Scenes 1 and 2" in repeated["detail"]


@pytest.mark.parametrize("language", SAMPLES)
def test_repeated_sentence_within_a_scene_is_caught(language):
    line = SAMPLES[language]
    passed, detail = ram_ai.check_repeated_narration([{"narration": f"{line}. {line}."}])
    assert not passed
    assert "twice" in detail


