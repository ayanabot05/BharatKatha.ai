"""One-off, cloud-only Indic Parler-TTS voice evaluation.

The HF token is read from Secret Manager in VM memory. Model weights stay on
the short-lived cloud VM. Only the generated sample and timings go to GCS.
"""

import base64
import json
import os
import time
import traceback
from pathlib import Path

import google.auth
from google.auth.transport.requests import AuthorizedSession
from google.cloud import storage

PROJECT = "ayana-video-studio"
BUCKET = "ayana-video-studio-voice-eval-20261014"
PREFIX = "indic-parler/2026-10-14"
SECRET = f"projects/{PROJECT}/secrets/indic-parler-hf-token/versions/latest:access"

SAMPLES = [
    (
        "lalitha_telugu",
        "మన ఊరి పాత మర్రిచెట్టు కింద ఒక వెండి పట్టీ దొరికింది. ఆ చిన్నారి సూర్యాస్తమయానికి ముందే దాన్ని అమ్మమ్మకు ఇచ్చింది.",
        "Lalitha speaks Telugu with a warm, natural storytelling voice, subtle emotion, a relaxed moderate pace, and clear pronunciation. The very clear audio is close and free of background noise.",
    ),
    (
        "prakash_telugu",
        "మన ఊరి పాత మర్రిచెట్టు కింద ఒక వెండి పట్టీ దొరికింది. ఆ చిన్నారి సూర్యాస్తమయానికి ముందే దాన్ని అమ్మమ్మకు ఇచ్చింది.",
        "Prakash speaks Telugu with a warm, natural storytelling voice, subtle emotion, a relaxed moderate pace, and clear pronunciation. The very clear audio is close and free of background noise.",
    ),
]


def main():
    started = time.monotonic()
    credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    session = AuthorizedSession(credentials)
    response = session.get(f"https://secretmanager.googleapis.com/v1/{SECRET}", timeout=30)
    response.raise_for_status()
    os.environ["HF_TOKEN"] = base64.b64decode(response.json()["payload"]["data"]).decode().strip()
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
    os.environ["HF_HOME"] = "/var/tmp/indic-parler-cache"

    import soundfile as sf
    import torch
    from parler_tts import ParlerTTSForConditionalGeneration
    from transformers import AutoTokenizer

    if not torch.cuda.is_available():
        raise RuntimeError("NVIDIA GPU is unavailable on the cloud VM")
    load_started = time.monotonic()
    model_id = "ai4bharat/indic-parler-tts"
    model = ParlerTTSForConditionalGeneration.from_pretrained(model_id, torch_dtype=torch.float16).to("cuda:0")
    model.eval()
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    description_tokenizer = AutoTokenizer.from_pretrained(model.config.text_encoder._name_or_path)
    load_seconds = round(time.monotonic() - load_started, 2)

    bucket = storage.Client(project=PROJECT).bucket(BUCKET)
    results = []
    for name, text, description in SAMPLES:
        description_inputs = description_tokenizer(description, return_tensors="pt").to("cuda:0")
        prompt_inputs = tokenizer(text, return_tensors="pt").to("cuda:0")
        start = time.monotonic()
        with torch.inference_mode():
            generation = model.generate(
                input_ids=description_inputs.input_ids,
                attention_mask=description_inputs.attention_mask,
                prompt_input_ids=prompt_inputs.input_ids,
                prompt_attention_mask=prompt_inputs.attention_mask,
            )
        generation_seconds = round(time.monotonic() - start, 2)
        audio = generation.float().cpu().numpy().squeeze()
        local_path = Path("/var/tmp") / f"{name}.wav"
        sf.write(local_path, audio, model.config.sampling_rate)
        object_name = f"{PREFIX}/{name}.wav"
        bucket.blob(object_name).upload_from_filename(str(local_path), content_type="audio/wav")
        results.append({
            "name": name,
            "text": text,
            "speaker_prompt": description,
            "sample_rate": model.config.sampling_rate,
            "duration_seconds": round(len(audio) / model.config.sampling_rate, 2),
            "generation_seconds": generation_seconds,
            "gcs_object": object_name,
        })
        local_path.unlink()

    report = {"status": "complete", "model": model_id, "gpu": torch.cuda.get_device_name(0),
              "load_seconds": load_seconds, "total_seconds": round(time.monotonic() - started, 2),
              "samples": results}
    bucket.blob(f"{PREFIX}/result.json").upload_from_string(
        json.dumps(report, ensure_ascii=False, indent=2), content_type="application/json")
    print("Cloud voice evaluation complete", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        # Never put the token or a response body in the error artifact.
        failure = {"status": "failed", "error_type": type(exc).__name__,
                   "error": str(exc)[:300], "traceback_tail": traceback.format_exc()[-1200:]}
        try:
            storage.Client(project=PROJECT).bucket(BUCKET).blob(f"{PREFIX}/result.json").upload_from_string(
                json.dumps(failure, ensure_ascii=False, indent=2), content_type="application/json")
        except Exception:
            pass
        raise
