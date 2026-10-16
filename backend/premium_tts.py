"""Operator priced, request bounded authorization for premium narration."""
import json
import os
from decimal import Decimal, InvalidOperation, ROUND_CEILING


PROVIDERS = {"google_chirp", "openai"}


def _money(value, label):
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise RuntimeError(f"{label} must be a finite INR amount") from exc
    if not amount.is_finite() or amount <= 0:
        raise RuntimeError(f"{label} must be a positive finite INR amount")
    return amount


def pricing():
    """Only expose premium routes with an operator supplied all-in upper rate."""
    try:
        configured = json.loads(os.environ.get("TTS_PREMIUM_RATES_JSON", "{}"))
    except json.JSONDecodeError as exc:
        raise RuntimeError("TTS_PREMIUM_RATES_JSON is invalid JSON") from exc
    if not isinstance(configured, dict):
        raise RuntimeError("TTS_PREMIUM_RATES_JSON must be a provider object")
    result = {}
    cap_raw = os.environ.get("TTS_PREMIUM_MAX_REQUEST_INR", "").strip()
    if not cap_raw:
        return result
    cap = _money(cap_raw, "TTS_PREMIUM_MAX_REQUEST_INR")
    for provider, entry in configured.items():
        if provider not in PROVIDERS or not isinstance(entry, dict):
            raise RuntimeError("TTS_PREMIUM_RATES_JSON contains an unknown provider")
        model_id = entry.get("model_id")
        if not isinstance(model_id, str) or not model_id.strip():
            raise RuntimeError(f"{provider} premium pricing lacks model_id")
        if provider == "openai" and model_id != os.environ.get("OPENAI_TTS_MODEL", "gpt-4o-mini-tts"):
            raise RuntimeError("OpenAI premium pricing model does not match the configured voice model")
        rate = _money(entry.get("all_in_inr_per_1000_chars"), f"{provider} all-in rate")
        if provider == "google_chirp" and entry.get("includes_caption_stt") is not True:
            raise RuntimeError("Google Chirp pricing must include caption transcription")
        result[provider] = {"model_id": model_id, "all_in_inr_per_1000_chars": str(rate),
                            "max_request_inr": str(cap)}
    return result


def quote(provider, texts):
    entry = pricing().get(provider)
    if not entry:
        raise RuntimeError(f"{provider} premium pricing and request cap are not configured")
    texts = list(texts)
    if any(not isinstance(text, str) for text in texts):
        raise RuntimeError("Premium narration must contain text strings")
    chars = sum(len(text) for text in texts)
    if chars <= 0:
        raise RuntimeError("Premium narration has no text")
    rate = Decimal(entry["all_in_inr_per_1000_chars"])
    # Each scene is a separate provider request, so round each request upward.
    amount = sum(((rate * len(text) / 1000).quantize(Decimal("0.01"), rounding=ROUND_CEILING)
                  for text in texts), Decimal("0"))
    return {"provider": provider, "model_id": entry["model_id"], "characters": chars,
            "estimated_cost_inr": float(amount), "operator_cap_inr": float(entry["max_request_inr"])}


def authorize(provider, texts, max_cost_inr):
    if provider not in PROVIDERS:
        return None
    estimate = quote(provider, texts)
    if max_cost_inr is None:
        raise RuntimeError("Enter a maximum INR budget before using a premium voice")
    budget = _money(max_cost_inr, "Premium voice budget")
    if budget > Decimal(str(estimate["operator_cap_inr"])):
        raise RuntimeError("Premium voice budget exceeds the operator request cap")
    if Decimal(str(estimate["estimated_cost_inr"])) > budget:
        raise RuntimeError("Premium voice estimate exceeds the permitted budget")
    return estimate
