"""Run a small, repeatable cloud-text benchmark for story promise delivery.

This is an automated acceptance sample, not a substitute for native-speaker
labels. Models run remotely through the configured text provider.
"""
import argparse
import asyncio
import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name(".env"))
os.environ["TEXT_PROVIDER"] = "vertex"

import ai  # noqa: E402


CASES = [
    ("te", "Andhra Pradesh", "Two neighbors repair a leaking village water pipe together. Keep the same two people throughout. No miracle or income claims."),
    ("te", "Telangana", "Mira finds Grandma's anklet near the village well and returns it to Grandma before sunset. Do not add a reward."),
    ("te", "Andhra Pradesh", "A farmer notices a broken irrigation hose, turns off the water, fits a connector, and only then restarts the flow. Do not promise a higher yield."),
    ("te", "Telangana", "A girl and her father discover seeds in an old clay pot. They identify the seeds together and decide to save them for the next planting season. No magical reveal."),
    ("hi", "Rajasthan", "Two sisters find a lost school bag at the bus stop and return it unopened to its owner before the bus leaves. Do not invent a cash reward."),
    ("hi", "Uttar Pradesh", "Tell the legend of Ghatotkacha protecting Arjuna during the Kurukshetra war, clearly as traditional storytelling. Show his sacrifice before the ending."),
    ("ta", "Tamil Nadu", "A grandmother teaches her grandson to repair a torn kite. Show the paper patch being attached before the kite flies again. Keep the same kite color."),
    ("mr", "Maharashtra", "A potter's daughter finds a crack in a clay water pot, sets that pot aside, and makes a new pot with her father. Do not claim the cracked pot was repaired."),
]


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=len(CASES))
    parser.add_argument("--cases", help="Comma-separated one-based case numbers")
    parser.add_argument("--tag", default="", help="Short report filename suffix")
    args = parser.parse_args()
    numbers = ([int(value) for value in args.cases.split(",")] if args.cases
               else list(range(1, max(1, min(args.limit, len(CASES))) + 1)))
    if not numbers or any(number < 1 or number > len(CASES) for number in numbers):
        parser.error("Case numbers must be within the benchmark set")
    selected = [(number, *CASES[number - 1]) for number in numbers]
    report = {"cases": [], "definition": "pass = generated script receives content_aligned and all_passed from independent app review"}
    for index, (number, language, region, idea) in enumerate(selected, 1):
        item = {"case": number, "language": language, "region": region, "idea": idea}
        started = time.monotonic()
        try:
            script = await ai.write_script(idea, language, region, 35, "Warm")
            contract = script.pop("_content_contract")
            item["script"] = {"title": script.get("title"), "scenes": script.get("scenes", [])}
            item["generation_seconds"] = round(time.monotonic() - started, 2)
            validation = await ai.validate_script(script, language, region, 35, idea, contract)
            item["review"] = {
                "overall": validation.get("overall"),
                "content_aligned": validation.get("content_aligned"),
                "all_passed": validation.get("all_passed"),
                "content_gaps": validation.get("content_gaps", []),
                "concept_misses": next((a.get("misses", []) for a in validation.get("agents", []) if a.get("key") == "concept"), []),
            }
            item["passed"] = bool(validation.get("content_aligned") and validation.get("all_passed"))
        except Exception as exc:
            item["passed"] = False
            item["error"] = f"{type(exc).__name__}: {str(exc)[:300]}"
        item["seconds"] = round(time.monotonic() - started, 2)
        report["cases"].append(item)
        print(f"{index}/{len(selected)} case {number} {language}: {'PASS' if item['passed'] else 'FAIL'} ({item['seconds']} s)", flush=True)
    passed = sum(bool(item["passed"]) for item in report["cases"])
    report["summary"] = {"passed": passed, "total": len(selected), "pass_rate": round(passed / len(selected), 3)}
    suffix = f"_{args.tag}" if args.tag else ""
    output = Path(__file__).resolve().parent.parent / "test_reports" / f"script_fidelity_benchmark_2026-10-14{suffix}.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Report: {output}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
