import asyncio
from copy import deepcopy
from unittest.mock import AsyncMock, patch

import pytest
import studio_copy


def test_display_translation_is_cached_and_does_not_mutate_story(tmp_path):
    async def run():
        project = {"id": "copy", "scenes": [{"visual": "Father enters the kitchen"}],
                   "script": {"scenes": [{"visual": "Father enters the kitchen"}]}}
        original = deepcopy(project)
        provider = AsyncMock(return_value='{"0":"నాన్న వంటగదిలోకి వెళ్తారు"}')
        with patch.object(studio_copy, "CACHE", tmp_path), patch.object(studio_copy.ai, "_text", provider):
            one, two = await asyncio.gather(studio_copy.translated_copy(project, "te"), studio_copy.translated_copy(project, "te"))
            assert one == two == {"Father enters the kitchen": "నాన్న వంటగదిలోకి వెళ్తారు"}
            assert await studio_copy.translated_copy(project, "te") == one
            assert provider.await_count == 1
            assert project == original
            project["scenes"][0]["visual"] = "Father cooks rice"
            project["script"] = {}
            await studio_copy.translated_copy(project, "te")
            assert provider.await_count == 2
    asyncio.run(run())


@pytest.mark.parametrize("response", ['{}', '{"0":"Still English"}', '{"0":null}'])
def test_incomplete_or_english_translation_is_not_cached(tmp_path, response):
    async def run():
        with patch.object(studio_copy, "CACHE", tmp_path), patch.object(studio_copy.ai, "_text", AsyncMock(return_value=response)):
            with pytest.raises(RuntimeError):
                await studio_copy.translated_copy({"id": "bad", "scenes": [{"visual": "Father cooks rice"}]}, "te")
            assert not list(tmp_path.rglob("*.json"))
    asyncio.run(run())


def test_native_copy_needs_no_provider_call():
    async def run():
        with patch.object(studio_copy.ai, "_text", AsyncMock()) as provider:
            assert await studio_copy.translated_copy({"id": "native", "scenes": [{"visual": "నాన్న వంట చేస్తున్నారు"}]}, "te") == {}
            provider.assert_not_awaited()
    asyncio.run(run())
