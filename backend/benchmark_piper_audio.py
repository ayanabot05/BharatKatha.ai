"""Run repeatable, real Piper-only speech probes against configured voice services.

This script never calls Chirp, Gemini, Edge or OpenAI. A configured Piper service
must already be running. Outputs require human/native-speaker listening review.
"""
import argparse
import asyncio
import json
import platform
import time
from pathlib import Path

import piper_tts
import render
from audio_eval_corpus import SCRIPTS


async def benchmark(language: str, output: Path) -> dict:
    entry = piper_tts.voices().get(language)
    if not entry:
        raise RuntimeError(f"No commercially reviewed Piper voice is configured for {language}")
    output.mkdir(parents=True, exist_ok=True)
    results = []
    for name, script in SCRIPTS[language].items():
        started = time.monotonic()
        speech = await piper_tts.synthesize(script, 1.0, language)
        elapsed = round(time.monotonic() - started, 3)
        path = output / f"{language}_{name}.mp3"
        path.write_bytes(speech["audio"])
        duration = render.duration(path)
        if duration <= 0:
            raise RuntimeError(f"Generated output could not be decoded: {path.name}")
        results.append({"case": name, "text": script, "file": path.name,
                        "bytes": len(speech["audio"]), "audio_seconds": duration,
                        "wall_seconds": elapsed, "synthesis_ms": speech["synthesis_ms"],
                        "caption_timing": speech["timing_source"]})
    report = {"provider": "piper", "model_id": piper_tts.model_signature(language),
              "license_source": entry["license_url"], "license_status": entry["license_status"],
              "configured_hardware_requirements": entry["hardware_requirements"],
              "runner": platform.platform(), "language": language,
              "estimated_cost_inr": None, "actual_cost_inr": None,
              "quality_review": "pending native-speaker listening", "results": results}
    (output / f"{language}_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--language", choices=sorted(SCRIPTS), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = asyncio.run(benchmark(args.language, args.output))
    print(json.dumps({"provider": result["provider"], "model_id": result["model_id"],
                      "language": result["language"], "cases": len(result["results"]),
                      "quality_review": result["quality_review"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
