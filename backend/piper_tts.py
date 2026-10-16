"""Adapter for an operator-hosted Piper HTTP server; no model is downloaded here."""
import json
import os
import time
from urllib.parse import urlparse

import httpx
from audio_eval_corpus import ALL_LANGUAGES


def voices() -> dict[str, dict]:
    """Only expose voices with an explicit commercial-license review record."""
    raw = os.environ.get("PIPER_VOICES_JSON", "{}").strip() or "{}"
    try:
        configured = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("PIPER_VOICES_JSON is invalid JSON") from exc
    if not isinstance(configured, dict):
        raise RuntimeError("PIPER_VOICES_JSON must be a language-to-voice object")
    result = {}
    for language, entry in configured.items():
        if not isinstance(language, str) or not isinstance(entry, dict):
            raise RuntimeError("PIPER_VOICES_JSON contains an invalid language or voice")
        if language not in ALL_LANGUAGES:
            raise RuntimeError(f"Piper voice language {language} is not offered by the app")
        required = ("url", "model_id", "model_revision", "license_url", "hardware_requirements")
        if any(not isinstance(entry.get(key), str) or not entry[key].strip() for key in required):
            raise RuntimeError(f"Piper voice {language} lacks model, license or hardware metadata")
        if not entry["url"].startswith(("http://", "https://")):
            raise RuntimeError(f"Piper voice {language} has an invalid service URL")
        if os.environ.get("APP_ENV") == "production":
            parsed = urlparse(entry["url"])
            if parsed.scheme != "https" or parsed.hostname in {"localhost", "127.0.0.1", "::1"}:
                raise RuntimeError(f"Piper voice {language} requires a remote HTTPS service in production")
            if entry.get("auth_audience") != entry["url"].rstrip("/"):
                raise RuntimeError(f"Piper voice {language} requires Cloud Run identity authentication")
        if entry.get("license_status") != "verified-commercial":
            raise RuntimeError(f"Piper voice {language} has no verified commercial license")
        result[language] = {**entry, "url": entry["url"].rstrip("/")}
    return result


def model_signature(language: str) -> str:
    entry = voices().get(language)
    return f"{entry['model_id']}@{entry['model_revision']}" if entry else "unavailable"


async def synthesize(text: str, speed: float, language: str) -> dict:
    entry = voices().get(language)
    if not entry:
        raise RuntimeError(f"Piper narration is not configured for language {language or 'unknown'}")
    started = time.monotonic()
    from cloud_identity import headers
    auth_headers = await headers(entry.get("auth_audience"))
    async with httpx.AsyncClient(timeout=90) as client:
        response = await client.post(f"{entry['url']}/synthesize", headers=auth_headers,
                                     json={"text": text, "length_scale": 1 / speed})
    if not response.is_success:
        raise RuntimeError(f"Piper narration failed (HTTP {response.status_code})")
    if not response.content or not response.content.startswith(b"RIFF"):
        raise RuntimeError("Piper returned invalid WAV audio")
    from render import to_mp3_bytes
    audio = to_mp3_bytes(response.content)
    return {"audio": audio, "words": [], "timing_source": "estimated",
            "model_id": model_signature(language), "synthesis_ms": round((time.monotonic() - started) * 1000)}
