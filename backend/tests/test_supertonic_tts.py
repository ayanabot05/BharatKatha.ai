"""Hindi local-provider license gate and explicit routing regression checks."""

import asyncio
import hashlib
from unittest.mock import AsyncMock, patch

import ai
import supertonic_tts


def test_hindi_model_is_hidden_without_reviewed_local_files(tmp_path):
    model = tmp_path / "model"
    onnx = model / "onnx"
    onnx.mkdir(parents=True)
    (model / "voice_styles").mkdir()
    (model / "LICENSE").write_bytes(b"fixture license")
    for filename in supertonic_tts.REQUIRED:
        (onnx / filename).touch()
    (model / "voice_styles" / "M1.json").touch()
    env = {"SUPERTONIC_HINDI_MODEL_DIR": str(model),
           "SUPERTONIC_HINDI_MODEL_REVISION": supertonic_tts.MODEL_REVISION}
    with patch.dict("os.environ", env), patch.object(supertonic_tts, "LICENSE_SHA256",
                                                      hashlib.sha256(b"fixture license").hexdigest()):
        assert supertonic_tts.available()
        assert supertonic_tts.model_signature("hi").startswith("supertonic-3/M1@")
        (model / "LICENSE").write_bytes(b"different terms")
        assert not supertonic_tts.available()
        (model / "LICENSE").write_bytes(b"fixture license")
        (onnx / "vocoder.onnx").unlink()
        assert not supertonic_tts.available()
    with patch.dict("os.environ", {**env, "SUPERTONIC_HINDI_MODEL_REVISION": "changed"}):
        assert not supertonic_tts.available()


def test_explicit_hindi_route_has_no_paid_fallback():
    result = {"audio": b"ID3real", "words": [], "timing_source": "estimated"}
    with patch.object(supertonic_tts, "synthesize", new=AsyncMock(return_value=result)) as local, \
         patch("premium_tts.authorize") as premium:
        actual = asyncio.run(ai.tts_timed("नमस्ते", "M1", 1.0, "hi", provider="supertonic"))
    assert actual == result
    local.assert_awaited_once_with("नमस्ते", 1.0, "hi", "M1")
    premium.assert_not_called()
