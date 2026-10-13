"""Convert explicitly reviewed examples into disjoint Gemini JSONL datasets.

Input rows: id, split (train/validation), prompt, response, reviewed=true,
permission_to_train=true. Response can be a string or a structured script.
This script performs no provider calls, uploads or training.
"""
import argparse
import hashlib
import json
from pathlib import Path


def prepare(rows):
    datasets = {"train": [], "validation": []}
    seen = set()
    for row in rows:
        if row.get("reviewed") is not True or row.get("permission_to_train") is not True:
            raise ValueError("Every example needs explicit review and training permission")
        split = row.get("split")
        prompt, response = row.get("prompt"), row.get("response")
        if split not in datasets or not isinstance(prompt, str) or not prompt.strip() or not response:
            raise ValueError("Each example needs a split, a prompt and a corrected response")
        key = hashlib.sha256(" ".join(prompt.split()).casefold().encode()).hexdigest()
        if key in seen:
            raise ValueError("Duplicate prompt; keep evaluation examples separate from training")
        seen.add(key)
        text = response if isinstance(response, str) else json.dumps(response, ensure_ascii=False)
        datasets[split].append({"contents": [
            {"role": "user", "parts": [{"text": prompt}]},
            {"role": "model", "parts": [{"text": text}]}]})
    if not all(datasets.values()):
        raise ValueError("Provide both training and held-out validation examples")
    return datasets


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    rows = [json.loads(line) for line in args.input.read_text(encoding="utf-8").splitlines() if line.strip()]
    datasets = prepare(rows)
    if args.output.exists():
        raise ValueError("Use a new output directory to preserve earlier dataset versions")
    args.output.mkdir(parents=True)
    for name, records in datasets.items():
        (args.output / f"{name}.jsonl").write_text(
            "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records), encoding="utf-8")
    print(json.dumps({k: len(v) for k, v in datasets.items()}))


if __name__ == "__main__":
    main()
