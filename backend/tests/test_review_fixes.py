import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import ai
import projects
import pytest


def test_creator_hooks_are_scoped_for_ideas_and_scripts():
    async def run():
        hooks = AsyncMock(return_value=[])
        contract = {"promise": "A story", "requirements": [{"source": "A story", "requirement": "Tell it"}]}
        with (patch.object(ai.pulse, "pulse_hooks_for", hooks),
              patch.object(ai, "ask_json", AsyncMock(return_value={"ideas": [], "scenes": [{"narration": "x"}]})),
              patch.object(ai, "extract_content_contract", AsyncMock(return_value=contract)),
              patch.object(ai, "_concept_preflight_gaps", AsyncMock(return_value=[])),
              patch.object(ai, "audit_scene_alignment", AsyncMock(return_value=[])),
              patch.object(ai, "audit_content_delivery", AsyncMock(return_value=[]))):
            await ai.suggest_ideas("en", "Delhi", "Family", "Shorts", "Families", "creator-a")
            await ai.write_script("A story", "en", "Delhi", 30, "Warm", user_id="creator-b")
        assert hooks.await_args_list[0].kwargs["user_id"] == "creator-a"
        assert hooks.await_args_list[1].kwargs["user_id"] == "creator-b"
    asyncio.run(run())


def test_two_named_sisters_does_not_forbid_the_bag_owner_from_appearing():
    async def run():
        idea = "Two sisters return a lost bag to its owner."
        extracted = {"promise": "Return the bag", "requirements": [
            {"source": "Two sisters", "requirement": "Exactly two characters appear", "action_words": []},
            {"source": "return a lost bag", "requirement": "Return the bag", "action_words": ["return"]}]}
        with patch.object(ai, "ask_json", AsyncMock(return_value=extracted)):
            contract = await ai.extract_content_contract(idea)
        assert contract["requirements"][0]["requirement"] == "Include the people named by the creator: Two sisters"
    asyncio.run(run())


def test_script_generation_keeps_short_topic_faithful_draft():
    async def run():
        draft = {"title": "The repaired pipe", "scenes": [{"narration": "A leak appears", "visual": "A leaking pipe"}]}
        generate = AsyncMock(return_value=draft)
        contract = {"promise": "Repair a village pipe", "requirements": [{"source": "Repair a village pipe", "requirement": "Repair it"}]}
        with (patch.object(ai, "ask_json", generate),
              patch.object(ai, "extract_content_contract", AsyncMock(return_value=contract)),
              patch.object(ai, "_concept_preflight_gaps", AsyncMock(return_value=[])),
              patch.object(ai, "audit_scene_alignment", AsyncMock(return_value=[])),
              patch.object(ai, "audit_content_delivery", AsyncMock(return_value=[]))):
            result = await ai.write_script("Repair a village pipe", "en", "Andhra Pradesh", 30, "Warm")
        assert result is draft
        assert generate.await_count == 1
        prompt = generate.await_args.args[1]
        assert "Satisfy the creator's idea first" in prompt
        assert "Do not add sentences solely to reach a duration or word count" in prompt
    asyncio.run(run())


def test_missing_promised_action_is_rewritten_before_script_is_returned():
    async def run():
        first = {"scenes": [{"narration": "They bring a clamp", "visual": "They hold it"}]}
        repaired = {"scenes": [{"narration": "They fit the clamp", "visual": "They fit it around the joint"}]}
        contract = {"promise": "Fit a clamp", "requirements": [{"source": "Fit a clamp", "requirement": "Fit it"}]}
        generate = AsyncMock(side_effect=[first, repaired])
        audit = AsyncMock(side_effect=[["Bringing the clamp is not fitting it"], []])
        with (patch.object(ai, "ask_json", generate),
              patch.object(ai, "adjudicate_story_gaps", AsyncMock(side_effect=lambda idea, script, gaps: gaps)),
              patch.object(ai, "extract_content_contract", AsyncMock(return_value=contract)),
              patch.object(ai, "_concept_preflight_gaps", AsyncMock(return_value=[])),
              patch.object(ai, "audit_scene_alignment", AsyncMock(return_value=[])),
              patch.object(ai, "audit_content_delivery", audit)):
            result = await ai.write_script("Fit a clamp", "en", "Andhra Pradesh", 30, "Warm")
        assert result is repaired
        assert generate.await_count == 2 and audit.await_count == 2
        assert "Bringing the clamp is not fitting it" in generate.await_args.args[1]
        assert "preserve scenes with no reported gap exactly" in generate.await_args.args[1]
    asyncio.run(run())


def test_unrepaired_promise_never_returns_a_script():
    async def run():
        draft = {"scenes": [{"narration": "They bring a clamp", "visual": "They hold it"}]}
        contract = {"promise": "Fit a clamp", "requirements": [{"source": "Fit a clamp", "requirement": "Fit it"}]}
        with (patch.object(ai, "ask_json", AsyncMock(return_value=draft)),
              patch.object(ai, "adjudicate_story_gaps", AsyncMock(side_effect=lambda idea, script, gaps: gaps)),
              patch.object(ai, "extract_content_contract", AsyncMock(return_value=contract)),
              patch.object(ai, "_concept_preflight_gaps", AsyncMock(return_value=[])),
              patch.object(ai, "audit_scene_alignment", AsyncMock(return_value=[])),
              patch.object(ai, "audit_content_delivery", AsyncMock(return_value=["Fitting is missing"]))):
            with pytest.raises(RuntimeError, match="still misses the selected content"):
                await ai.write_script("Fit a clamp", "en", "Andhra Pradesh", 30, "Warm")
    asyncio.run(run())


def test_content_audit_does_not_count_holding_as_fitting():
    async def run():
        contract = {"promise": "Fit the clamp", "requirements": [
            {"source": "fit the clamp", "requirement": "Fit the clamp", "action_words": ["fit", "attach"]}]}
        draft = {"scenes": [{"narration": "They brought the clamp",
                             "visual": "They hold the clamp against the joint"}]}
        optimistic_review = {"keeps_promise": True, "checks": [
            {"number": 1, "delivered": True, "scene": 1, "field": "visual",
             "quote": "hold the clamp against the joint", "gap": ""}], "overall_gap": ""}
        with patch.object(ai, "ask_json", AsyncMock(return_value=optimistic_review)):
            gaps = await ai.audit_content_delivery("fit the clamp", contract, draft)
        assert gaps == ["Scene 1 only holds or brings the part; it does not show: Fit the clamp"]
    asyncio.run(run())


def test_content_audit_allows_real_actions_described_with_synonyms():
    async def run():
        contract = {"promise": "Return an envelope", "requirements": [
            {"source": "returns the envelope", "requirement": "Mira returns the envelope",
             "action_words": ["return"]}]}
        draft = {"scenes": [{"narration": "Mira returned it to her teacher",
                             "visual": "Mira hands the unopened envelope to her teacher"}]}
        review = {"keeps_promise": True, "checks": [
            {"number": 1, "delivered": True, "scene": 1, "field": "visual",
             "quote": "hands the unopened envelope", "gap": ""}], "overall_gap": ""}
        with patch.object(ai, "ask_json", AsyncMock(return_value=review)):
            assert await ai.audit_content_delivery("returns the envelope", contract, draft) == []
    asyncio.run(run())


def test_farmer_role_is_verified_in_visual_when_model_cites_wrong_language_field():
    async def run():
        contract = {"promise": "A farmer repairs a hose", "requirements": [
            {"source": "A farmer", "requirement": "The protagonist must be a farmer", "action_words": []}]}
        script = {"scenes": [{"narration": "రైతు గొట్టం చూస్తాడు", "visual": "A farmer inspects the hose"}]}
        review = {"keeps_promise": True, "checks": [
            {"number": 1, "delivered": True, "scene": 1, "field": "narration",
             "quote": "farmer", "gap": ""}], "overall_gap": ""}
        with patch.object(ai, "ask_json", AsyncMock(return_value=review)):
            assert await ai.audit_content_delivery("A farmer repairs a hose", contract, script) == []
    asyncio.run(run())


def test_turning_off_pump_is_visible_evidence_of_stopping_water():
    async def run():
        contract = {"promise": "Turn off water before repair", "requirements": [
            {"source": "turns off the water", "requirement": "The farmer must turn off the water",
             "action_words": ["turn"]}]}
        script = {"scenes": [{"narration": "రైతు పంపు ఆపాడు",
                              "visual": "The farmer turns off the electrical pump switch"}]}
        review = {"keeps_promise": True, "checks": [
            {"number": 1, "delivered": True, "scene": 1, "field": "narration",
             "quote": "turns off the water", "gap": ""}], "overall_gap": ""}
        with patch.object(ai, "ask_json", AsyncMock(return_value=review)):
            assert await ai.audit_content_delivery("A farmer turns off the water", contract, script) == []
    asyncio.run(run())


def test_hindi_legend_framing_is_verified_from_narration():
    async def run():
        contract = {"promise": "A Mahabharata legend", "requirements": [
            {"source": "clearly as traditional storytelling",
             "requirement": "Use the traditional storytelling style", "action_words": []}]}
        script = {"scenes": [{"narration": "महाभारत की कथा में घटोत्कच अर्जुन की रक्षा करता है।",
                              "visual": "Ghatotkacha protects Arjuna on the battlefield"}]}
        review = {"keeps_promise": True, "checks": [
            {"number": 1, "delivered": True, "scene": 1, "field": "narration",
             "quote": "traditional storytelling", "gap": ""}], "overall_gap": ""}
        with patch.object(ai, "ask_json", AsyncMock(return_value=review)):
            assert await ai.audit_content_delivery("Tell a legend clearly as traditional storytelling", contract, script) == []
    asyncio.run(run())


def test_requested_kite_color_is_repeated_without_overwriting_a_conflict():
    script = {"scenes": [{"visual": "A torn red paper kite"},
                         {"visual": "Grandma holds the paper kite"},
                         {"visual": "A blue kite flies"}]}
    ai._fill_requested_kite_color("Keep the same kite color", script)
    assert script["scenes"][1]["visual"] == "Grandma holds the red paper kite"
    assert script["scenes"][2]["visual"] == "A blue kite flies"
    assert not ai._consistent_kite_color(script["scenes"])


def test_time_condition_cannot_be_proved_by_an_earlier_scene():
    async def run():
        idea = "Mira returns the anklet to Grandma before sunset."
        contract = {"promise": "Return the anklet before sunset", "requirements": [
            {"source": "returns the anklet to Grandma", "requirement": "Return the anklet", "action_words": ["returns"]},
            {"source": "before sunset", "requirement": "Return before sunset", "action_words": []}]}
        draft = {"scenes": [
            {"narration": "Mira walks before sunset", "visual": "The sun is above the village path"},
            {"narration": "Mira gives Grandma the anklet", "visual": "Mira hands Grandma the anklet on the porch"}]}
        review = {"keeps_promise": True, "checks": [
            {"number": 1, "delivered": True, "scene": 2, "field": "visual", "quote": "Mira hands Grandma the anklet", "gap": ""},
            {"number": 2, "delivered": True, "scene": 1, "field": "narration", "quote": "before sunset", "gap": ""}], "overall_gap": ""}
        with patch.object(ai, "ask_json", AsyncMock(return_value=review)):
            gaps = await ai.audit_content_delivery(idea, contract, draft)
        assert any("action shot" in gap and "Scene 2" in gap for gap in gaps)
    asyncio.run(run())


def test_relative_before_action_does_not_require_one_scene():
    async def run():
        idea = "Attach the patch before the kite flies again."
        contract = {"promise": "Patch before flight", "requirements": [
            {"source": "Attach the patch", "requirement": "Attach the patch", "action_words": ["attach"]},
            {"source": "before the kite flies again", "requirement": "Kite flies after patching", "action_words": []}]}
        draft = {"scenes": [
            {"narration": "Grandma attaches the patch", "visual": "Grandma attaches paper to the kite"},
            {"narration": "The kite flies again", "visual": "The patched kite flies above the field"}]}
        review = {"keeps_promise": True, "checks": [
            {"number": 1, "delivered": True, "scene": 1, "field": "visual", "quote": "attaches paper", "gap": ""},
            {"number": 2, "delivered": True, "scene": 2, "field": "visual", "quote": "kite flies", "gap": ""}],
            "overall_gap": ""}
        with patch.object(ai, "ask_json", AsyncMock(return_value=review)):
            assert await ai.audit_content_delivery(idea, contract, draft) == []
    asyncio.run(run())


def test_incomplete_content_checklist_gets_one_retry():
    async def run():
        contract = {"promise": "Find the letter", "requirements": [
            {"source": "Find the letter", "requirement": "Find the letter", "action_words": ["find"]}]}
        draft = {"scenes": [{"narration": "Mira finds the letter", "visual": "Mira picks up a letter"}]}
        complete = {"keeps_promise": True, "checks": [
            {"number": 1, "delivered": True, "scene": 1, "field": "narration", "quote": "finds the letter", "gap": ""}],
            "overall_gap": ""}
        model = AsyncMock(side_effect=[{"keeps_promise": True, "checks": []}, complete])
        with patch.object(ai, "ask_json", model):
            assert await ai.audit_content_delivery("Find the letter", contract, draft) == []
        assert model.await_count == 2
    asyncio.run(run())


def test_content_checklist_retries_invented_quote_before_rewriting_story():
    async def run():
        contract = {"promise": "Find a letter", "requirements": [
            {"source": "finds a letter", "requirement": "Find the letter", "action_words": ["find"]}]}
        script = {"scenes": [{"narration": "Mira finds a letter", "visual": "Mira picks up a letter"}]}
        wrong = {"keeps_promise": True, "checks": [
            {"number": 1, "delivered": True, "scene": 1, "field": "visual",
             "quote": "Mira finds a letter", "gap": ""}], "overall_gap": ""}
        right = {"keeps_promise": True, "checks": [
            {"number": 1, "delivered": True, "scene": 1, "field": "visual",
             "quote": "Mira picks up a letter", "gap": ""}], "overall_gap": ""}
        model = AsyncMock(side_effect=[wrong, right])
        with patch.object(ai, "ask_json", model):
            assert await ai.audit_content_delivery("Mira finds a letter", contract, script) == []
        assert model.await_count == 2
    asyncio.run(run())


def test_visual_rejects_two_moments_in_one_still():
    script = {"scenes": [
        {"visual": "The girl runs along the road, then hands the anklet to Grandma."},
        {"visual": "The girl hands the anklet to Grandma on the porch."}]}
    assert ai.visual_shot_gaps(script) == [
        "Scene 1 visual describes multiple moments; show only the final action in one still image"]


def test_scene_alignment_blocks_action_shown_before_narration():
    async def run():
        script = {"scenes": [{"narration": "Somayya, turn the valve",
                              "visual": "Somayya turns the valve handle"}]}
        review = {"scene_checks": [{"scene": 1, "aligned": False,
                                    "issue": "The image shows the turn while narration still asks for it",
                                    "narration_quote": "turn the valve",
                                    "visual_quote": "turns the valve handle"}]}
        with patch.object(ai, "ask_json", AsyncMock(return_value=review)):
            gaps = await ai.audit_scene_alignment(script, "en")
        assert len(gaps) == 1 and "out of sync" in gaps[0]
    asyncio.run(run())


def test_scene_alignment_requires_quotes_from_the_same_scene():
    async def run():
        script = {"scenes": [{"narration": "They inspect the leak", "visual": "Two neighbors inspect the pipe"}]}
        invented = {"scene_checks": [{"scene": 1, "aligned": False, "issue": "Repair shown early",
                                      "narration_quote": "They inspect the leak",
                                      "visual_quote": "They finish the repair"}]}
        with patch.object(ai, "ask_json", AsyncMock(return_value=invented)):
            with pytest.raises(RuntimeError, match="outside its scene"):
                await ai.audit_scene_alignment(script, "en")
    asyncio.run(run())


def test_scene_alignment_retries_an_invented_citation():
    async def run():
        script = {"scenes": [{"narration": "They inspect the leak", "visual": "Two neighbors inspect the pipe"}]}
        invented = {"scene_checks": [{"scene": 1, "aligned": False, "issue": "Repair shown early",
                                      "narration_quote": "They inspect the leak", "visual_quote": "They finish the repair"}]}
        corrected = {"scene_checks": [{"scene": 1, "aligned": True, "issue": "",
                                       "narration_quote": "", "visual_quote": ""}]}
        model = AsyncMock(side_effect=[invented, corrected])
        with patch.object(ai, "ask_json", model):
            assert await ai.audit_scene_alignment(script, "en") == []
        assert model.await_count == 2
    asyncio.run(run())


def test_scene_alignment_accepts_complete_action_in_both_fields():
    async def run():
        script = {"scenes": [{"narration": "Somayya turns the valve", "visual": "Somayya turns the valve handle"}]}
        review = {"scene_checks": [{"scene": 1, "aligned": True, "issue": "",
                                    "narration_quote": "", "visual_quote": ""}]}
        with patch.object(ai, "ask_json", AsyncMock(return_value=review)):
            assert await ai.audit_scene_alignment(script, "en") == []
    asyncio.run(run())


def test_concept_preflight_blocks_story_with_scene_order_mismatch():
    async def run():
        review = {"aligned": False, "misses": ["Scene 3: narration says the hand is released while the visual holds it"]}
        with patch.object(ai, "_agent", AsyncMock(return_value=review)):
            gaps = await ai._concept_preflight_gaps({"scenes": []}, "te", "Andhra Pradesh", "Two neighbors repair a pipe")
        assert gaps == review["misses"]
    asyncio.run(run())


def test_concept_preflight_retries_invalid_citation_without_accepting_it():
    async def run():
        review = {"aligned": True, "misses": []}
        agent = AsyncMock(side_effect=[RuntimeError("Concept review cited scene evidence that does not exist"), review])
        with patch.object(ai, "_agent", agent):
            assert await ai._concept_preflight_gaps({"scenes": []}, "te", "Andhra Pradesh", "A story") == []
        assert agent.await_count == 2
    asyncio.run(run())


def test_exclusion_requires_whole_script_review_not_unrelated_quote():
    async def run():
        idea = "Mira returns the anklet. Do not add a reward."
        contract = {"promise": "Return without a reward", "requirements": [
            {"source": "Do not add a reward", "requirement": "No reward", "action_words": []}]}
        draft = {"scenes": [{"narration": "Mira goes home", "visual": "Mira walks home"}]}
        review = {"keeps_promise": True, "checks": [
            {"number": 1, "delivered": True, "scene": 1, "field": "visual", "quote": "Mira walks home", "gap": ""}],
            "overall_gap": ""}
        with patch.object(ai, "ask_json", AsyncMock(return_value=review)):
            gaps = await ai.audit_content_delivery(idea, contract, draft)
        assert any("every scene" in gap for gap in gaps)
    asyncio.run(run())


def test_character_continuity_requires_whole_script_review():
    async def run():
        idea = "Keep the same two characters throughout."
        contract = {"promise": "Same pair", "requirements": [
            {"source": idea, "requirement": "Keep the same two characters", "action_words": []}]}
        draft = {"scenes": [
            {"narration": "Mira and Ravi see a leak", "visual": "Mira and Ravi beside the pipe"},
            {"narration": "They fix it", "visual": "Mira and Ravi fit a clamp"}]}
        one_scene = {"keeps_promise": True, "checks": [
            {"number": 1, "delivered": True, "scene": 1, "field": "visual",
             "quote": "Mira and Ravi beside the pipe", "gap": ""}], "overall_gap": ""}
        full_review = {"keeps_promise": True, "checks": [
            {"number": 1, "delivered": True, "scene": 0, "field": "all_scenes",
             "quote": "", "gap": ""}], "overall_gap": ""}
        with patch.object(ai, "ask_json", AsyncMock(side_effect=[one_scene, full_review])):
            assert any("character evidence" in gap for gap in await ai.audit_content_delivery(idea, contract, draft))
            assert await ai.audit_content_delivery(idea, contract, draft) == []
    asyncio.run(run())


def test_exact_cast_size_uses_all_scenes_evidence():
    async def run():
        idea = "A story about two neighbours."
        contract = {"promise": "Two neighbours", "requirements": [
            {"source": "two neighbours", "requirement": "Exactly two characters who are neighbors.",
             "action_words": []}]}
        draft = {"characters": [{"name": "Mira"}, {"name": "Ravi"}], "scenes": [
            {"narration": "Neighbors Mira and Ravi spot a leak", "visual": "Mira and Ravi by the pipe"},
            {"narration": "They fix it", "visual": "Mira and Ravi fit a clamp"}]}
        review = {"keeps_promise": True, "checks": [
            {"number": 1, "delivered": True, "scene": 1, "field": "all_scenes", "quote": "", "gap": ""}],
            "overall_gap": ""}
        scene_review = {"keeps_promise": True, "checks": [
            {"number": 1, "delivered": True, "scene": 1, "field": "narration",
             "quote": "Neighbors Mira and Ravi", "gap": ""}], "overall_gap": ""}
        with patch.object(ai, "ask_json", AsyncMock(side_effect=[review, scene_review])):
            assert await ai.audit_content_delivery(idea, contract, draft) == []
            assert await ai.audit_content_delivery(idea, contract, draft) == []
    asyncio.run(run())


def test_exact_cast_size_recognizes_neighbor_character_wording():
    async def run():
        contract = {"promise": "Two neighbours", "requirements": [
            {"source": "two neighbours", "requirement": "There must be exactly two neighbor characters.",
             "action_words": []}]}
        draft = {"characters": [{"name": "Mira"}, {"name": "Ravi"}], "scenes": [
            {"narration": "Mira and Ravi, the two neighbors, spot a leak", "visual": "Two neighbors by a pipe"}]}
        review = {"keeps_promise": True, "checks": [
            {"number": 1, "delivered": True, "scene": 1, "field": "all_scenes", "quote": "", "gap": ""}],
            "overall_gap": ""}
        with patch.object(ai, "ask_json", AsyncMock(return_value=review)):
            assert await ai.audit_content_delivery("two neighbours", contract, draft) == []
    asyncio.run(run())


def test_village_setting_can_be_checked_in_scene_visuals():
    async def run():
        contract = {"promise": "A village story", "requirements": [
            {"source": "original fictional village", "requirement": "The setting must be an original fictional village.",
             "action_words": []}]}
        review = {"keeps_promise": True, "checks": [
            {"number": 1, "delivered": True, "scene": 1, "field": "all_scenes", "quote": "", "gap": ""}],
            "overall_gap": ""}
        village = {"scenes": [{"narration": "They see the leak", "visual": "Two neighbors on a village lane"}]}
        city = {"scenes": [{"narration": "They see the leak", "visual": "Two neighbors on a city street"}]}
        with patch.object(ai, "ask_json", AsyncMock(side_effect=[review, review])):
            assert await ai.audit_content_delivery("original fictional village", contract, village) == []
            assert await ai.audit_content_delivery("original fictional village", contract, city)
    asyncio.run(run())


def test_visible_leak_and_two_character_cast_survive_bad_static_citations():
    async def run():
        idea = "A leaking water pipe. Keep the same two characters throughout."
        contract = {"promise": "Fix the leak", "requirements": [
            {"source": "A leaking water pipe", "requirement": "A water pipe must be leaking", "action_words": []},
            {"source": "Keep the same two characters throughout", "requirement": "Same two characters throughout", "action_words": []}]}
        draft = {"characters": [{"name": "Mira"}, {"name": "Ravi"}], "scenes": [
            {"narration": "They see water escaping", "visual": "A metal pipe leaking water beside Mira and Ravi"}]}
        review = {"keeps_promise": True, "checks": [
            {"number": 1, "delivered": True, "scene": 1, "field": "visual", "quote": "water pipe leaking", "gap": ""},
            {"number": 2, "delivered": True, "scene": 1, "field": "visual", "quote": "Mira and Ravi", "gap": ""}],
            "overall_gap": ""}
        with patch.object(ai, "ask_json", AsyncMock(return_value=review)):
            assert await ai.audit_content_delivery(idea, contract, draft) == []
    asyncio.run(run())


def test_visible_leak_does_not_prove_repair_action():
    async def run():
        idea = "Repair a leaking water pipe."
        contract = {"promise": "Repair it", "requirements": [
            {"source": "Repair a leaking water pipe", "requirement": "Repair the leaking pipe", "action_words": ["repair"]}]}
        draft = {"scenes": [{"narration": "They notice the leak", "visual": "A metal pipe leaking water"}]}
        review = {"keeps_promise": True, "checks": [
            {"number": 1, "delivered": True, "scene": 1, "field": "visual", "quote": "They repair it", "gap": ""}],
            "overall_gap": ""}
        with patch.object(ai, "ask_json", AsyncMock(return_value=review)):
            assert await ai.audit_content_delivery(idea, contract, draft)
    asyncio.run(run())


def test_two_sisters_relationship_has_visible_scene_evidence():
    async def run():
        idea = "Two sisters return a bag."
        contract = {"promise": "Sisters help", "requirements": [
            {"source": "Two sisters", "requirement": "The protagonists are two sisters", "action_words": []}]}
        draft = {"scenes": [{"narration": "दोनों बहनें बैग देखती हैं", "visual": "Two sisters see a blue bag"}]}
        review = {"keeps_promise": True, "checks": [
            {"number": 1, "delivered": True, "scene": 1, "field": "visual", "quote": "unrelated quote", "gap": ""}],
            "overall_gap": ""}
        with patch.object(ai, "ask_json", AsyncMock(return_value=review)):
            assert await ai.audit_content_delivery(idea, contract, draft) == []
    asyncio.run(run())


def test_find_evidence_uses_requested_object_not_any_pickup():
    assert ai._visible_find_evidence(
        "Mira finds Grandma's anklet near the well",
        [{"visual": "Mira picking up the silver anklet near the well"}])
    assert not ai._visible_find_evidence(
        "Mira finds Grandma's anklet near the well",
        [{"visual": "Mira picking up a pebble near the well"}])


def test_visible_family_role_survives_bad_static_citation():
    async def run():
        contract = {"promise": "Grandma and grandson", "requirements": [
            {"source": "grandmother", "requirement": "The story includes a grandmother character", "action_words": []}]}
        draft = {"scenes": [{"narration": "பாட்டி கற்றுக்கொடுக்கிறாள்",
                              "visual": "A grandmother guiding her grandson's hands"}]}
        review = {"keeps_promise": True, "checks": [
            {"number": 1, "delivered": True, "scene": 1, "field": "visual",
             "quote": "wrong quote", "gap": ""}], "overall_gap": ""}
        with patch.object(ai, "ask_json", AsyncMock(return_value=review)):
            assert await ai.audit_content_delivery("A grandmother helps", contract, draft) == []
    asyncio.run(run())


def test_kite_repair_prompt_keeps_patches_out_of_earlier_shots():
    project = {"style": "storybook", "region": "Tamil Nadu", "script": {"characters": []},
               "scenes": [
                   {"id": "a", "visual": "A boy holds a torn red kite"},
                   {"id": "b", "visual": "The boy's hands attach a paper patch to the red kite"},
                   {"id": "c", "visual": "The red kite flies after repair"}]}
    first, second, third = project["scenes"]
    assert "no patch, tape, glue" in ai.scene_prompt(project, first, False)
    assert "ONE new paper patch" in ai.scene_prompt(project, second, True)
    assert "ONE completed visible paper patch" in ai.scene_prompt(project, third, True)


def test_kite_color_must_be_explicit_and_consistent_in_each_shot():
    assert ai._consistent_kite_color([
        {"visual": "A blue paper kite lies on the table"},
        {"visual": "Grandma attaches a patch to the blue kite"},
        {"visual": "The blue kite flies over the field"}])
    assert not ai._consistent_kite_color([
        {"visual": "A blue kite lies on the table"},
        {"visual": "The red kite flies over the field"}])
    assert not ai._consistent_kite_color([
        {"visual": "A blue kite lies on the table"},
        {"visual": "The kite flies over the field"}])


def test_contract_accepts_atomic_requirements_returned_as_a_list():
    async def run():
        original = {"promise": "Find and return a letter", "requirements": [
            {"source": "find a letter and return it", "requirement": "Find a letter and return it",
             "action_words": ["find", "return"]}]}
        split = [
            {"source": "find a letter", "requirement": "Find a letter", "action_words": ["find"]},
            {"source": "return it", "requirement": "Return the letter", "action_words": ["return"]},
        ]
        with patch.object(ai, "ask_json", AsyncMock(side_effect=[original, split])):
            contract = await ai.extract_content_contract("find a letter and return it")
        assert contract["promise"] == original["promise"]
        assert contract["requirements"] == split
    asyncio.run(run())


def test_content_contract_restores_idea_capitalization_without_accepting_a_paraphrase():
    async def run():
        contract = {"promise": "A village story", "requirements": [
            {"source": "an original fictional village", "requirement": "Village setting", "action_words": []}]}
        with patch.object(ai, "ask_json", AsyncMock(return_value=contract)):
            result = await ai._extract_content_contract_once("An original fictional village story")
        assert result["requirements"][0]["source"] == "An original fictional village"
    asyncio.run(run())


def test_content_contract_restores_shared_negation_for_atomic_exclusion():
    async def run():
        contract = {"promise": "A grounded village story", "requirements": [
            {"source": "no income claims", "requirement": "No income claims", "action_words": []}]}
        idea = "Tell a village story. No miracle or income claims."
        with patch.object(ai, "ask_json", AsyncMock(return_value=contract)):
            result = await ai._extract_content_contract_once(idea)
        assert result["requirements"][0]["source"] == "No miracle or income claims"
    asyncio.run(run())


def test_content_contract_expands_conjunction_source_to_shared_negation():
    async def run():
        contract = {"promise": "A grounded village story", "requirements": [
            {"source": "or income claims", "requirement": "No income claims", "action_words": []}]}
        idea = "Tell a village story. No miracle or income claims."
        with patch.object(ai, "ask_json", AsyncMock(return_value=contract)):
            result = await ai._extract_content_contract_once(idea)
        assert result["requirements"][0]["source"] == "No miracle or income claims"
    asyncio.run(run())


def test_script_review_reuses_the_project_content_contract():
    async def run():
        contract = {"promise": "Return the envelope", "requirements": [
            {"source": "return it", "requirement": "Return it", "action_words": ["return"]}]}
        script = {"scenes": [{"narration": "Mira returns it", "visual": "Mira hands it to the teacher"}]}

        async def agent(key, name, brief, script, language, region, idea):
            return {"key": key, "name": name, "score": 90, "fixes": [],
                    **({"aligned": True, "misses": []} if key == "concept" else {}),
                    **({"safe": True} if key == "safety" else {})}

        checks = {"all_passed": True, "safety_passed": True, "checks": [], "fixes": [], "disclaimer": ""}
        with (patch.object(ai, "_agent", side_effect=agent),
              patch.object(ai, "adjudicate_story_gaps", AsyncMock(side_effect=lambda idea, script, gaps: gaps)),
              patch.object(ai.ram_ai, "run_ram_ai_checks", return_value=checks),
              patch.object(ai, "extract_content_contract", AsyncMock(side_effect=AssertionError("re-extracted"))),
              patch.object(ai, "audit_content_delivery", AsyncMock(return_value=[])) as audit):
            result = await ai.validate_script(script, "en", "Rajasthan", 30, "return it", contract)
        assert result["all_passed"] and result["content_aligned"]
        assert audit.await_args.args[1] is contract
    asyncio.run(run())


def test_script_review_retries_bad_citations_without_skipping_evidence():
    async def run():
        script = {"scenes": [{"narration": "She waters the tree", "visual": "Girl beside the tree"}]}
        seen = {"concept": 0}

        async def agent(key, name, brief, script, language, region, idea):
            if key == "concept":
                seen["concept"] += 1
                if seen["concept"] < 3:
                    raise RuntimeError("Concept review cited invalid scene alignment evidence")
            return {"key": key, "name": name, "score": 90, "fixes": [],
                    **({"aligned": True, "misses": []} if key == "concept" else {}),
                    **({"safe": True} if key == "safety" else {})}

        checks = {"all_passed": True, "safety_passed": True, "checks": [], "fixes": [], "disclaimer": ""}
        with (patch.object(ai, "_agent", side_effect=agent),
              patch.object(ai.ram_ai, "run_ram_ai_checks", return_value=checks)):
            result = await ai.validate_script(script, "te", "Andhra Pradesh", 45)
        assert seen["concept"] == 3
        assert result["all_passed"]
    asyncio.run(run())


def test_script_review_never_accepts_persistently_bad_citations():
    async def run():
        with patch.object(ai, "_agent", AsyncMock(side_effect=RuntimeError(
                "Concept review cited invalid scene alignment evidence"))) as agent:
            try:
                await ai.validate_script({"scenes": []}, "te", "Andhra Pradesh", 45)
            except RuntimeError as exc:
                assert "invalid scene alignment evidence" in str(exc)
            else:
                raise AssertionError("Malformed evidence must block approval")
        assert agent.await_count == 3
    asyncio.run(run())


def test_independent_content_gap_blocks_an_optimistic_concept_review():
    async def run():
        contract = {"promise": "Fit the clamp", "requirements": [
            {"source": "fit the clamp", "requirement": "Fit it", "action_words": ["fit"]}]}
        script = {"scenes": [{"narration": "They bring it", "visual": "They hold it near the joint"}]}

        async def agent(key, name, brief, script, language, region, idea):
            return {"key": key, "name": name, "score": 90, "fixes": [],
                    **({"aligned": True, "misses": []} if key == "concept" else {}),
                    **({"safe": True} if key == "safety" else {})}

        checks = {"all_passed": True, "safety_passed": True, "checks": [], "fixes": [], "disclaimer": ""}
        with (patch.object(ai, "_agent", side_effect=agent),
              patch.object(ai.ram_ai, "run_ram_ai_checks", return_value=checks),
              patch.object(ai, "adjudicate_story_gaps", AsyncMock(return_value=["The clamp is never fitted"])),
              patch.object(ai, "audit_content_delivery", AsyncMock(return_value=["The clamp is never fitted"]))):
            result = await ai.validate_script(script, "en", "Andhra Pradesh", 30, "fit the clamp", contract)
        assert result["concept_aligned"] is True
        assert result["content_aligned"] is False
        assert result["all_passed"] is False
        assert "The clamp is never fitted" in result["fixes"]
    asyncio.run(run())


def test_generated_content_contract_is_saved_separately_from_the_script():
    async def run():
        contract = {"promise": "Return the envelope", "requirements": [
            {"source": "return it", "requirement": "Return it", "action_words": ["return"]}]}
        draft = {"title": "Mira", "scenes": [{"narration": "She returns it", "visual": "She hands it back"}],
                 "_content_contract": contract}
        project = {"id": "project", "render": {"status": "idle"}}
        with (patch.object(projects, "owned", AsyncMock(return_value=project)),
              patch.object(projects, "check_daily_limit", AsyncMock()),
              patch.object(projects.ai, "write_script", AsyncMock(return_value=draft)),
              patch.object(projects, "upd", AsyncMock()) as update,
              patch.object(projects.pulse, "log_event", AsyncMock())):
            await projects.gen_script("project", projects.ScriptIn(idea="return it", language="en"), {"id": "creator"})
        fields = update.await_args.kwargs
        assert fields["content_contract"] is contract
        assert "_content_contract" not in fields["script"]
        assert fields["scenes"][0]["visual"] == "She hands it back"
    asyncio.run(run())


def test_improved_script_is_kept_unapproved_when_reviewer_citation_is_invalid():
    async def run():
        contract = {"promise": "Repair the pipe", "requirements": []}
        improved = {"title": "The pipe", "scenes": [
            {"narration": "They fix the pipe", "visual": "Two workers fix the pipe"}],
            "_content_contract": contract}
        project = {"id": "project", "idea": "Repair the pipe", "language": "en", "region": "Delhi",
                   "render": {"status": "idle"}, "script": {"scenes": []},
                   "validation": {"agents": [], "ram_ai_fixes": []}}
        with (patch.object(projects, "owned", AsyncMock(return_value=project)),
              patch.object(projects.ai, "write_script", AsyncMock(return_value=improved)),
              patch.object(projects.ai, "validate_script", AsyncMock(side_effect=RuntimeError("invalid citation"))),
              patch.object(projects, "upd", AsyncMock()) as update):
            await projects.improve("project", {"id": "creator"})
        fields = update.await_args.kwargs
        assert fields["validation"] is None
        assert fields["approved"] is False
        assert fields["script"] is improved
        assert fields["content_contract"] is contract
    asyncio.run(run())


def test_scene_mismatch_blocks_concept_approval():
    idea = "Inspect the leaking pipe, then fit a clamp."
    script = {"scenes": [
        {"narration": "They inspect the leaking pipe.", "visual": "They inspect the leaking pipe."},
        {"narration": "The pipe is still leaking.", "visual": "They fit a clamp to the pipe."},
    ]}
    review = {
        "aligned": True, "misses": [],
        "requirements": [{"source": "Inspect the leaking pipe", "status": "met",
                          "evidence": [{"scene": 1, "field": "visual", "quote": "inspect the leaking pipe"}]},
                         {"source": "fit a clamp", "status": "met",
                          "evidence": [{"scene": 2, "field": "visual", "quote": "fit a clamp"}]}],
        "scene_checks": [
            {"scene": 1, "aligned": True, "narration_quote": "inspect the leaking pipe",
             "visual_quote": "inspect the leaking pipe", "issue": ""},
            {"scene": 2, "aligned": False, "narration_quote": "still leaking",
             "visual_quote": "fit a clamp", "issue": "The clamp appears before narration describes fitting it."},
        ],
    }
    ai.validate_concept_evidence(review, script, idea)
    assert review["aligned"] is False
    assert "Scene 2" in review["misses"][0]


def test_concept_review_rejects_missing_or_invented_scene_evidence():
    idea = "Fit a clamp."
    script = {"scenes": [{"narration": "They fit a clamp.", "visual": "A clamp is fitted."}]}
    review = {"aligned": True, "misses": [],
              "requirements": [{"source": "Fit a clamp", "status": "met",
                                "evidence": [{"scene": 1, "field": "visual", "quote": "a different pipe"}]}],
              "scene_checks": [{"scene": 1, "aligned": True, "narration_quote": "fit a clamp",
                                "visual_quote": "A clamp is fitted", "issue": ""}]}
    with pytest.raises(RuntimeError, match="evidence that does not exist"):
        ai.validate_concept_evidence(review, script, idea)


def test_edit_uses_earlier_shot_as_authority_for_recurring_props():
    async def run():
        scene = {"id": "shot-2", "image_path": "current.png", "visual": "Close-up of the pipe joint"}
        project = {"style": "cartoon", "scenes": [scene]}
        collection = SimpleNamespace(find_one=AsyncMock(return_value=project), update_one=AsyncMock())
        with (patch.object(projects, "db", SimpleNamespace(projects=collection)),
              patch.object(projects, "get_object", AsyncMock(return_value=(b"current", "image/png"))),
              patch.object(projects, "save_media", AsyncMock(return_value="new.png")),
              patch.object(ai, "audit_scene_image", AsyncMock(return_value=[])),
              patch.object(ai, "gen_image", AsyncMock(return_value=(b"new", "image/png", False))) as generate):
            await projects._scene_job("project", "user", "shot-2", "Show the repaired joint", b"earlier")
        prompt, refs = generate.await_args.args
        assert refs == [b"current", b"earlier"]
        assert "second image is the authoritative earlier view" in prompt
        assert "Close-up of the pipe joint" in prompt
    asyncio.run(run())


def test_scene_image_retries_review_gap_before_becoming_ready():
    async def run():
        scene = {"id": "s1", "visual": "Grandma shows an unpatched torn kite", "narration": "It is still torn"}
        project = {"id": "p1", "scenes": [scene]}
        collection = SimpleNamespace(find_one=AsyncMock(return_value=project), update_one=AsyncMock())
        generate = AsyncMock(side_effect=[(b"premature-patch", "image/png", False),
                                          (b"still-torn", "image/png", False)])
        audit = AsyncMock(side_effect=[["A patch is already attached"], []])
        with (patch.object(projects, "db", SimpleNamespace(projects=collection)),
              patch.object(projects, "save_media", AsyncMock(return_value="accepted.png")),
              patch.object(ai, "gen_image", generate), patch.object(ai, "audit_scene_image", audit)):
            assert await projects._scene_job("p1", "user", "s1") == (b"still-torn", False)
        assert generate.await_count == 2
        assert "A patch is already attached" in generate.await_args.args[0]
        assert collection.update_one.await_args.args[1]["$set"]["scenes.$.status"] == "ready"
    asyncio.run(run())


def test_scene_image_with_two_bad_reviews_is_not_approved():
    async def run():
        scene = {"id": "s1", "visual": "A torn kite", "narration": "The kite tore"}
        collection = SimpleNamespace(find_one=AsyncMock(return_value={"scenes": [scene]}), update_one=AsyncMock())
        save = AsyncMock()
        with (patch.object(projects, "db", SimpleNamespace(projects=collection)),
              patch.object(projects, "save_media", save),
              patch.object(ai, "gen_image", AsyncMock(return_value=(b"wrong", "image/png", False))),
              patch.object(ai, "audit_scene_image", AsyncMock(return_value=["The kite is already repaired"]))):
            assert await projects._scene_job("p1", "user", "s1") is None
        save.assert_not_awaited()
        assert collection.update_one.await_args.args[1]["$set"]["scenes.$.status"] == "failed"
        assert collection.update_one.await_args.args[1]["$set"]["scenes.$.approved"] is False
    asyncio.run(run())


def test_image_quota_is_not_hidden_by_unsupported_fallback():
    class Client:
        def __init__(self):
            self.aio = self
            self.models = SimpleNamespace(generate_content=AsyncMock(side_effect=[
                RuntimeError("429 RESOURCE_EXHAUSTED"), RuntimeError("404 NOT_FOUND"),
                RuntimeError("429 RESOURCE_EXHAUSTED"), RuntimeError("429 RESOURCE_EXHAUSTED")]))

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

    async def run():
        client = Client()
        with (patch.object(ai, "IMAGE_PROVIDER", "developer"),
              patch.object(ai, "FALLBACK_IMAGE_MODELS", ["available", "unsupported"]),
              patch.object(ai, "ALLOW_IMAGE_FALLBACK", False),
              patch.object(ai, "_key", return_value="unused"),
              patch.object(ai.genai, "Client", return_value=client),
              patch.object(ai.asyncio, "sleep", AsyncMock())):
            with pytest.raises(ai.ImageQuotaError):
                await ai.gen_image("a pipe")
    asyncio.run(run())


def test_script_review_retries_incomplete_scene_inspection_and_case_only_source():
    async def run():
        idea = "A girl waters a small mango sapling."
        script = {"scenes": [{"narration": "ఆమె మొక్కకు నీరు పోసింది", "visual": "A girl waters a small mango sapling"}]}
        seen = {"concept": 0}

        async def agent(key, name, brief, script, language, region, idea):
            if key == "concept":
                seen["concept"] += 1
                if seen["concept"] == 1:
                    raise RuntimeError("Concept review did not inspect every scene; please retry")
                if seen["concept"] == 2:
                    raise RuntimeError("Concept review skipped or repeated a scene")
                review = {
                    "key": key, "name": name, "score": 90, "fixes": [], "aligned": True, "misses": [],
                    "requirements": [{
                        "source": "a girl waters a small mango sapling",
                        "status": "met",
                        "evidence": [{"scene": 1, "field": "visual", "quote": " A girl waters a small mango sapling "}],
                    }],
                    "scene_checks": [{
                        "scene": 1, "aligned": True,
                        "narration_quote": " ఆమె మొక్కకు నీరు పోసింది ",
                        "visual_quote": " A girl waters a small mango sapling ",
                        "issue": "",
                    }],
                }
                ai.validate_concept_evidence(review, script, idea)
                return review
            return {"key": key, "name": name, "score": 90, "fixes": [],
                    **({"safe": True} if key == "safety" else {})}

        checks = {"all_passed": True, "safety_passed": True, "checks": [], "fixes": [], "disclaimer": ""}
        with (patch.object(ai, "_agent", side_effect=agent),
              patch.object(ai.ram_ai, "run_ram_ai_checks", return_value=checks),
              patch.object(ai, "extract_content_contract", AsyncMock(return_value={
                  "promise": "Water the sapling",
                  "requirements": [{"source": "A girl waters a small mango sapling", "requirement": "Water the sapling", "action_words": ["waters"]}],
              })),
              patch.object(ai, "audit_content_delivery", AsyncMock(return_value=[]))):
            result = await ai.validate_script(script, "te", "Andhra Pradesh", 45, idea)
        assert seen["concept"] == 3
        assert result["all_passed"] is True
        assert result["concept_aligned"] is True
    asyncio.run(run())

