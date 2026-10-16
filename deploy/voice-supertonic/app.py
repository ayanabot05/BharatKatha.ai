"""Private CPU Hindi voice service. Weights are staged in GCS, not on a laptop."""

import asyncio
import hashlib
import io
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

REVISION = "aafc6e32416a594460b32413efc49d7fe4ce6d46"
LICENSE_SHA256 = "0d944a9110fed9a9602d60e0423a272903e7bd21ab060490774efc77c2275e9f"
FILES = ["LICENSE", "onnx/duration_predictor.onnx", "onnx/text_encoder.onnx",
         "onnx/vector_estimator.onnx", "onnx/vocoder.onnx", "onnx/tts.json",
         "onnx/unicode_indexer.json", "voice_styles/M1.json"]
app = FastAPI(title="BharatKatha Hindi voice")
model = None
style = None
lock = asyncio.Lock()


class Speech(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    speed: float = Field(ge=0.7, le=2.0)
    voice: str = "M1"
    language: str = "hi"


def load_model():
    from google.cloud import storage
    from supertonic import TTS

    if os.environ.get("SUPERTONIC_HINDI_MODEL_REVISION") != REVISION:
        raise RuntimeError("Hindi model revision is not pinned to the reviewed version")
    bucket = storage.Client().bucket(os.environ["VOICE_MODEL_BUCKET"])
    prefix = os.environ["VOICE_MODEL_PREFIX"].strip("/")
    if not prefix:
        raise RuntimeError("VOICE_MODEL_PREFIX is required")
    root = Path("/tmp/supertonic-model")
    for name in FILES:
        dst = root / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        bucket.blob(f"{prefix}/{name}").download_to_filename(str(dst), timeout=240)
    if hashlib.sha256((root / "LICENSE").read_bytes()).hexdigest() != LICENSE_SHA256:
        raise RuntimeError("Hindi model license hash does not match the reviewed version")
    instance = TTS(model="supertonic-3", model_dir=root, auto_download=False, intra_op_num_threads=4)
    return instance, instance.get_voice_style("M1")


@app.on_event("startup")
async def startup():
    global model, style
    model, style = await asyncio.to_thread(load_model)


@app.get("/health")
async def health():
    return {"ok": model is not None, "model_revision": REVISION}


@app.post("/synthesize")
async def synthesize(body: Speech):
    if body.voice != "M1" or body.language not in {"hi", "en"} or model is None:
        raise HTTPException(400, "Reviewed Hindi M1 voice is unavailable")
    async with lock:
        def generate():
            import soundfile as sf
            wav, _ = model.synthesize(body.text, voice_style=style, lang=body.language,
                                      speed=body.speed, total_steps=8)
            output = io.BytesIO()
            sf.write(output, wav.reshape(-1), model.sample_rate, format="WAV", subtype="PCM_16")
            return output.getvalue()
        data = await asyncio.to_thread(generate)
    return Response(data, media_type="audio/wav")
