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
              patch.object(ai, "audit_content_delivery", AsyncMock(return_value=[]))):
            await ai.suggest_ideas("en", "Delhi", "Family", "Shorts", "Families", "creator-a")
            await ai.write_script("A story", "en", "Delhi", 30, "Warm", user_id="creator-b")
        assert hooks.await_args_list[0].kwargs["user_id"] == "creator-a"
        assert hooks.await_args_list[1].kwargs["user_id"] == "creator-b"
    asyncio.run(run())


def test_script_generation_keeps_short_topic_faithful_draft():
    async def run():
        draft = {"title": "The repaired pipe", "scenes": [{"narration": "A leak appears", "visual": "A leaking pipe"}]}
        generate = AsyncMock(return_value=draft)
        contract = {"promise": "Repair a village pipe", "requirements": [{"source": "Repair a village pipe", "requirement": "Repair it"}]}
        with (patch.object(ai, "ask_json", generate),
              patch.object(ai, "extract_content_contract", AsyncMock(return_value=contract)),
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
              patch.object(ai, "extract_content_contract", AsyncMock(return_value=contract)),
              patch.object(ai, "audit_content_delivery", audit)):
            result = await ai.write_script("Fit a clamp", "en", "Andhra Pradesh", 30, "Warm")
        assert result is repaired
        assert generate.await_count == 2 and audit.await_count == 2
        assert "Bringing the clamp is not fitting it" in generate.await_args.args[1]
    asyncio.run(run())


def test_unrepaired_promise_never_returns_a_script():
    async def run():
        draft = {"scenes": [{"narration": "They bring a clamp", "visual": "They hold it"}]}
        contract = {"promise": "Fit a clamp", "requirements": [{"source": "Fit a clamp", "requirement": "Fit it"}]}
        with (patch.object(ai, "ask_json", AsyncMock(return_value=draft)),
              patch.object(ai, "extract_content_contract", AsyncMock(return_value=contract)),
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
              patch.object(ai.ram_ai, "run_ram_ai_checks", return_value=checks),
              patch.object(ai, "extract_content_contract", AsyncMock(side_effect=AssertionError("re-extracted"))),
              patch.object(ai, "audit_content_delivery", AsyncMock(return_value=[])) as audit):
            result = await ai.validate_script(script, "en", "Rajasthan", 30, "return it", contract)
        assert result["all_passed"] and result["content_aligned"]
        assert audit.await_args.args[1] is contract
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
              patch.object(ai, "gen_image", AsyncMock(return_value=(b"new", "image/png", False))) as generate):
            await projects._scene_job("project", "user", "shot-2", "Show the repaired joint", b"earlier")
        prompt, refs = generate.await_args.args
        assert refs == [b"current", b"earlier"]
        assert "second image is the authoritative earlier view" in prompt
        assert "Close-up of the pipe joint" in prompt
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
