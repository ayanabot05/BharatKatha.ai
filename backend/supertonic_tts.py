"""Pinned Supertonic 3 Hindi/English provider; never downloads or falls back."""

import asyncio
import hashlib
import io
import os
from pathlib import Path
import threading
import time
from urllib.parse import urlparse

MODEL_REVISION = "aafc6e32416a594460b32413efc49d7fe4ce6d46"
LICENSE_SHA256 = "0d944a9110fed9a9602d60e0423a272903e7bd21ab060490774efc77c2275e9f"
REQUIRED = ("duration_predictor.onnx", "text_encoder.onnx", "vector_estimator.onnx",
            "vocoder.onnx", "tts.json", "unicode_indexer.json")
_model = None
_loaded_from = None
_lock = threading.Lock()


def model_dir() -> Path | None:
    raw = os.environ.get("SUPERTONIC_HINDI_MODEL_DIR", "").strip()
    return Path(raw).expanduser().resolve() if raw else None


def available() -> bool:
    """Expose only the pinned, locally present model with its reviewed license."""
    service_url = os.environ.get("SUPERTONIC_HINDI_SERVICE_URL", "").strip()
    if service_url:
        parsed = urlparse(service_url)
        return (os.environ.get("SUPERTONIC_HINDI_MODEL_REVISION") == MODEL_REVISION
                and parsed.scheme == "https" and parsed.hostname not in {"localhost", "127.0.0.1", "::1"})
    if os.environ.get("APP_ENV") == "production":
        return False
    path = model_dir()
    if not path or os.environ.get("SUPERTONIC_HINDI_MODEL_REVISION") != MODEL_REVISION:
        return False
    license_path = path / "LICENSE"
    try:
        if hashlib.sha256(license_path.read_bytes()).hexdigest() != LICENSE_SHA256:
            return False
        return all((path / "onnx" / name).is_file() for name in REQUIRED) and \
            (path / "voice_styles" / "M1.json").is_file()
    except OSError:
        return False


def model_signature(language: str) -> str:
    return f"supertonic-3/M1@{MODEL_REVISION}" if language in {"hi", "en"} and available() else "unavailable"


def _synthesize(text: str, speed: float, voice: str, language: str) -> dict:
    global _model, _loaded_from
    if not available():
        raise RuntimeError("The licensed local Hindi Supertonic model is not configured")
    if voice != "M1":
        raise RuntimeError("Only the evaluated Supertonic Hindi M1 voice is enabled")
    if not 0.7 <= speed <= 2.0:
        raise RuntimeError("Supertonic speed must be between 0.7 and 2.0")
    started = time.monotonic()
    with _lock:
        path = model_dir()
        if _model is None or _loaded_from != path:
            try:
                from supertonic import TTS
            except ImportError as exc:
                raise RuntimeError("Local Supertonic package is not installed") from exc
            _model = TTS(model="supertonic-3", model_dir=path, auto_download=False,
                         intra_op_num_threads=4)
            _loaded_from = path
        style = _model.get_voice_style("M1")
        wav, _ = _model.synthesize(text, voice_style=style, lang=language, speed=speed,
                                   total_steps=8)
        import soundfile as sf
        output = io.BytesIO()
        sf.write(output, wav.reshape(-1), _model.sample_rate, format="WAV", subtype="PCM_16")
    from render import to_mp3_bytes
    audio = to_mp3_bytes(output.getvalue())
    if not audio or audio[:3] not in (b"ID3", b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"):
        raise RuntimeError("Supertonic returned invalid MP3 audio")
    return {"audio": audio, "words": [], "timing_source": "estimated",
            "model_id": model_signature(language),
            "synthesis_ms": round((time.monotonic() - started) * 1000)}


async def synthesize(text: str, speed: float, language: str, voice: str) -> dict:
    if language not in {"hi", "en"}:
        raise RuntimeError(f"Supertonic is unavailable for language {language or 'unknown'}")
    service_url = os.environ.get("SUPERTONIC_HINDI_SERVICE_URL", "").rstrip("/")
    if service_url:
        if not available() or voice != "M1" or not 0.7 <= speed <= 2.0:
            raise RuntimeError("The reviewed Hindi cloud voice is unavailable")
        import httpx
        from cloud_identity import headers
        from render import to_mp3_bytes
        started = time.monotonic()
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(f"{service_url}/synthesize",
                headers=await headers(service_url),
                json={"text": text, "speed": speed, "voice": voice, "language": language})
        response.raise_for_status()
        if not response.content.startswith(b"RIFF"):
            raise RuntimeError("Hindi cloud voice returned invalid WAV audio")
        audio = await asyncio.to_thread(to_mp3_bytes, response.content)
        return {"audio": audio, "words": [], "timing_source": "estimated",
                "model_id": model_signature("hi"),
                "synthesis_ms": round((time.monotonic() - started) * 1000)}
    return await asyncio.to_thread(_synthesize, text, speed, voice, language)
