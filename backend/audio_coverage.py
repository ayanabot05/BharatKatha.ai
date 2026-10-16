"""Report evidence stages for all creation languages without claiming quality."""
import argparse
import hashlib
import json
from pathlib import Path

from audio_eval_corpus import ALL_LANGUAGES, CASES, PRIMARY_LANGUAGES, SCRIPTS


def evidence_for(language: str, report_root: Path) -> dict:
    """A report counts only when every expected case has a nonempty audio file."""
    found = []
    for report_path in sorted(report_root.glob(f"*-audio-{language}-*/{language}_report.json")):
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
            results = report.get("results", [])
            cases = {item["case"] for item in results}
            valid = (report.get("language") == language and bool(report.get("provider"))
                     and bool(report.get("model_id")) and cases == set(CASES)
                     and len(results) == len(CASES)
                     and all((report_path.parent / item["file"]).is_file()
                             and (report_path.parent / item["file"]).stat().st_size > 0
                             and item.get("audio_seconds", 0) > 0 for item in results))
            if valid:
                found.append({"provider": report.get("provider"), "model_id": report.get("model_id"),
                              "report": str(report_path), "cases": len(results)})
        except (OSError, ValueError, KeyError, TypeError):
            continue
    for report_path in sorted(report_root.glob("supertonic-*/report.json")):
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
            cases = report.get("cases", {})
            valid = report.get("language") == language and set(cases) == set(CASES)
            for item in cases.values():
                sample = report_path.parent / Path(item["mp3_path"]).name
                valid = valid and sample.is_file() and sample.stat().st_size == item["mp3_bytes"]
                valid = valid and hashlib.sha256(sample.read_bytes()).hexdigest() == item["mp3_sha256"]
                valid = valid and item["audio_duration_seconds"] > 0 and item["inference"]["wall_seconds"] > 0
            if valid:
                found.append({"provider": report["provider"],
                              "model_id": f"{report['model_repo']}@{report['model_revision']}",
                              "report": str(report_path), "cases": len(cases)})
        except (OSError, ValueError, KeyError, TypeError):
            continue
    return {"language": language, "priority": "primary" if language in PRIMARY_LANGUAGES else "secondary",
            "requested_completion_target_pct": 100 if language in PRIMARY_LANGUAGES else 90,
            "corpus_cases": len(SCRIPTS[language]), "real_sample_evidence": found,
            "stage": "samples_recorded" if found else "corpus_ready",
            "native_speaker_review": "pending", "app_end_to_end": "pending"}


def coverage(report_root: Path) -> dict:
    rows = [evidence_for(language, report_root) for language in ALL_LANGUAGES]
    return {"languages": rows,
            "primary_cohort_sample_complete": all(row["real_sample_evidence"] for row in rows if row["priority"] == "primary"),
            "all_language_sample_complete": all(row["real_sample_evidence"] for row in rows),
            "quality_status": "unscored; fluent-speaker rubric required"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report-root", type=Path, default=Path(__file__).resolve().parent.parent / "test_reports")
    args = parser.parse_args()
    print(json.dumps(coverage(args.report_root), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
