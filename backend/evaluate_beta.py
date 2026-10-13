"""Exercise the running beta using remote providers, without local model inference.

Creates a labelled evaluation project; never trains on or exports existing users' data.
Run from backend: python evaluate_beta.py --language te
"""
import argparse
import json
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--language", choices=["te", "mr"], default="te")
    parser.add_argument("--image", action="store_true", help="Generate one remote scene image")
    parser.add_argument("--voice", action="store_true", help="Generate one short remote voice preview")
    parser.add_argument("--improve", action="store_true", help="Apply reviewer feedback and save a second candidate (not model training)")
    args = parser.parse_args()
    load_dotenv(Path(__file__).with_name(".env"))
    session = requests.Session()
    report = {"language": args.language, "checks": [], "outputs": {}, "training_performed": False}
    output = Path(__file__).parent / "evaluations" / f"beta-{args.language}-{int(time.time())}.json"
    output.parent.mkdir(exist_ok=True)

    def request(method, path, body=None):
        started = time.monotonic()
        response = session.request(method, args.base_url + "/api" + path, json=body, timeout=180)
        report["checks"].append({"path": path, "status": response.status_code,
                                 "seconds": round(time.monotonic() - started, 2)})
        print(f"{method} {path}: {response.status_code}", flush=True)
        if response.status_code >= 400:
            # Provider exception bodies can contain credentials. Do not store them.
            raise RuntimeError(f"Request failed at {path}: HTTP {response.status_code}")
        return response

    try:
        request("GET", "/health")
        request("POST", "/auth/login", {"email": os.environ["ADMIN_EMAIL"], "password": os.environ["ADMIN_PASSWORD"]})
        request("GET", "/auth/me")
        region = "Andhra Pradesh" if args.language == "te" else "Maharashtra"
        ideas = request("POST", "/ideas/suggest", {"language": args.language, "region": region,
                        "category": "Village life", "audience": "First-time adult creators", "platform": "YouTube Shorts"}).json()
        report["outputs"]["ideas"] = ideas
        p = request("POST", "/projects", {"title": "BETA EVALUATION: village cooperation", "language": args.language, "region": region}).json()
        pid = p["id"]
        report["project_id"] = pid
        p = request("POST", f"/projects/{pid}/script/generate", {
            "idea": "An original fictional village story: two neighbours repair a leaking water pipe together. Keep the same two characters throughout. No miracle or income claims.",
            "language": args.language, "region": region, "duration": 30, "tone": "Emotional"}).json()
        report["outputs"]["script"] = p["script"]
        p = request("POST", f"/projects/{pid}/script/validate").json()
        report["outputs"]["validation"] = p["validation"]
        if args.improve:
            p = request("POST", f"/projects/{pid}/script/improve").json()
            report["outputs"]["revised_script"] = p["script"]
            report["outputs"]["revised_validation"] = p["validation"]
        if args.voice:
            audio = request("POST", "/voice/preview", {"text": p["scenes"][0]["narration"][:250], "voice": "fable", "speed": 1.0, "language": args.language})
            output.with_suffix(".mp3").write_bytes(audio.content)
            report["outputs"]["voice"] = {"bytes": len(audio.content), "content_type": audio.headers.get("content-type")}
        if args.image:
            request("PATCH", f"/projects/{pid}", {"style": "cartoon"})
            sid = p["scenes"][0]["id"]
            request("POST", f"/projects/{pid}/scenes/{sid}/regenerate", {})
            deadline = time.monotonic() + 180
            while time.monotonic() < deadline:
                p = request("GET", f"/projects/{pid}").json()
                scene = p["scenes"][0]
                if scene["status"] != "generating":
                    report["outputs"]["image"] = {k: scene.get(k) for k in ("status", "placeholder", "image_path")}
                    break
                time.sleep(5)
            else:
                report["outputs"]["image"] = {"status": "timeout"}
        image = report["outputs"].get("image", {})
        report["result"] = ("failed: real image generation unavailable" if args.image and
                            (image.get("placeholder") or image.get("status") != "ready") else
                            "completed; native-language and image review still required")
    except Exception as exc:
        report["result"] = type(exc).__name__ + ": " + str(exc)[:200]
        print(report["result"], flush=True)
    finally:
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Report: {output}", flush=True)


if __name__ == "__main__":
    main()
