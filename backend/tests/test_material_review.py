import asyncio
from unittest.mock import AsyncMock, patch

import pytest
import ai


def test_missing_required_step_remains_blocked():
    response = {"decisions": [{"number": 1, "blocking": True, "reason": "The clamp is never fitted",
                                "scene": 0, "quote": "", "source": "fit the clamp"}]}
    with patch.object(ai, "ask_json", AsyncMock(return_value=response)):
        result = asyncio.run(ai.adjudicate_story_gaps("They must fit the clamp", {"scenes": [
            {"narration": "They bring it", "visual": "They hold a clamp"}]}, ["Fitting missing"]))
    assert result == ["The clamp is never fitted"]


def test_harmless_wording_can_be_advisory():
    response = {"decisions": [{"number": 1, "blocking": False, "reason": "Same pump action",
                                "scene": 0, "quote": "", "source": ""}]}
    with patch.object(ai, "ask_json", AsyncMock(return_value=response)):
        assert asyncio.run(ai.adjudicate_story_gaps("Turn off the water", {"scenes": [
            {"narration": "He stops the pump", "visual": "His hand turns off the pump switch"}]},
            ["Different words used"])) == []


def test_invented_blocking_evidence_never_becomes_a_verdict():
    response = {"decisions": [{"number": 1, "blocking": True, "reason": "Wrong action",
                                "scene": 1, "quote": "He burns the kite", "source": ""}]}
    with patch.object(ai, "ask_json", AsyncMock(return_value=response)) as model:
        with pytest.raises(RuntimeError, match="invalid evidence"):
            asyncio.run(ai.adjudicate_story_gaps("Repair the kite", {"scenes": [
                {"narration": "He repairs it", "visual": "He attaches a patch"}]}, ["Wrong action"]))
    assert model.await_count == 2


def test_cleared_reviewer_error_is_not_sent_back_as_a_required_rewrite():
    async def run():
        async def agent(key, name, brief, script, language, region, idea):
            return {"key": key, "name": name, "score": 84, "fixes": [],
                    **({"aligned": False, "misses": ["The owner is a forbidden third character"]}
                       if key == 'concept' else {}),
                    **({"safe": True} if key == 'safety' else {})}
        checks = {"all_passed": True, "safety_passed": True, "checks": [], "fixes": [], "disclaimer": ""}
        with (patch.object(ai, '_agent', side_effect=agent),
              patch.object(ai.ram_ai, 'run_ram_ai_checks', return_value=checks),
              patch.object(ai, 'audit_content_delivery', AsyncMock(return_value=[])),
              patch.object(ai, 'adjudicate_story_gaps', AsyncMock(return_value=[]))):
            result = await ai.validate_script({"scenes": [{"narration": "They return it", "visual": "Two sisters return the bag to its owner"}]},
                                              'en', 'Delhi', 30, 'Two sisters return a bag to its owner', {"requirements": []})
        assert result['all_passed'] and result['content_aligned']
        assert result['review_advisories'] == ['The owner is a forbidden third character']
        assert not result['fixes']
        assert not next(a for a in result['agents'] if a['key'] == 'concept')['misses']
    asyncio.run(run())
