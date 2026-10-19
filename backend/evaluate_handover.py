"""End-to-end handover dry run: idea -> script -> review -> images -> Piper voice -> MP4.

This follows the real creator path (not a pre-baked script), so it exercises the
same endpoints the phone UI calls. It reads ADMIN_EMAIL/ADMIN_PASSWORD from
backend/.env and never prints secrets.

Usage (backend server must already be running):
    python evaluate_handover.py --base-url http://127.0.0.1:8001 --language te --provider piper
    # resume an already reviewed project straight from image generation:
    python evaluate_handover.py --base-url http://127.0.0.1:8001 --project <id>
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "test_reports" / "handover_dry_run"


def build_idea(idea: dict) -> str:
    return "\n".join(part for part in [
        f"Selected story: {idea.get('title_en') or idea.get('title') or ''}",
        f"Story promise: {idea.get('logline') or ''}",
        f"Opening question or hook: {idea.get('hook') or ''}",
        f"Required payoff: {idea.get('payoff') or ''}",
    ] if part.split(":", 1)[-1].strip())


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8001")
    parser.add_argument("--language", default="te")
    parser.add_argument("--region", default="Andhra Pradesh")
    parser.add_argument("--duration", type=int, default=30)
    parser.add_argument("--voice", default="coral")
    parser.add_argument("--provider", default="piper")
    parser.add_argument("--project", help="Resume an existing reviewed project id, starting at images")
    parser.add_argument("--timeout-images", type=int, default=900)
    args = parser.parse_args()

    load_dotenv(Path(__file__).with_name(".env"))
    OUT.mkdir(parents=True, exist_ok=True)
    base = args.base_url.rstrip("/") + "/api"
    client = httpx.Client(timeout=300, follow_redirects=True)

    def call(method, path, body=None, timeout=300):
        response = client.request(method, base + path, json=body, timeout=timeout)
        if not response.is_success:
            try:
                detail = json.dumps(response.json())[:400]
            except Exception:
                detail = response.text[:400]
            raise RuntimeError(f"{method} {path}: HTTP {response.status_code} {detail}")
        return response.json()

    print("1. login", flush=True)
    me = call("POST", "/auth/login", {"email": os.environ["ADMIN_EMAIL"], "password": os.environ["ADMIN_PASSWORD"]})
    print("   user:", me.get("email"), "role:", me.get("role"), flush=True)

    if args.project:
        print("2. resume reviewed project", args.project, flush=True)
        project = call("GET", f"/projects/{args.project}")
        pid = project["id"]
        if not project.get("approved"):
            raise RuntimeError("Cannot resume: the script has not been approved")
        if not project.get("style"):
            project = call("PATCH", f"/projects/{pid}", {"style": "storybook"})
        print("   approved:", project.get("approved"), "style:", project.get("style"),
              "scenes:", len(project.get("scenes") or []), flush=True)
    else:
        print("2. suggest ideas", flush=True)
        ideas = call("POST", "/ideas/suggest", {"language": args.language, "region": args.region,
                                                "category": "Moral stories", "platform": "YouTube Shorts",
                                                "audience": "Families & kids"})["ideas"]
        if not ideas:
            raise RuntimeError("No ideas were suggested")
        idea = ideas[0]
        print("   title:", idea.get("title_en") or idea.get("title"), flush=True)

        print("3. create project", flush=True)
        project = call("POST", "/projects", {"title": "Handover dry run", "language": args.language, "region": args.region})
        pid = project["id"]
        print("   project:", pid, flush=True)

        print("4. generate script", flush=True)
        project = call("POST", f"/projects/{pid}/script/generate", {
            "idea": build_idea(idea), "language": args.language, "region": args.region, "duration": args.duration,
            "tone": "Emotional", "category": "Moral stories", "audience": "Families & kids",
            "platform": "YouTube Shorts"}, timeout=420)
        print("   scenes:", len(project.get("scenes") or []), "title:", (project.get("script") or {}).get("title"), flush=True)

        print("5. review script", flush=True)
        for attempt in range(3):
            project = call("POST", f"/projects/{pid}/script/validate", timeout=420)
            if (project.get("validation") or {}).get("all_passed"):
                break
            print(f"   review attempt {attempt + 1} not passed; applying fixes", flush=True)
            try:
                project = call("POST", f"/projects/{pid}/script/improve", timeout=420)
            except RuntimeError as exc:
                print("   improve failed:", exc, flush=True)
                break
        if not (project.get("validation") or {}).get("all_passed"):
            print("   REVIEW BLOCKED:", json.dumps((project.get("validation") or {}).get("content_gaps"), ensure_ascii=False), flush=True)
            (OUT / "state.json").write_text(json.dumps({"project_id": pid, "stage": "review_blocked",
                                                        "validation": project.get("validation")}, ensure_ascii=False, indent=2), encoding="utf-8")
            return 2
        print("   review passed", flush=True)

        print("6. approve script + style", flush=True)
        call("POST", f"/projects/{pid}/script/approve")
        call("PATCH", f"/projects/{pid}", {"style": "storybook"})

    print("7. generate scene images", flush=True)
    call("POST", f"/projects/{pid}/scenes/generate")
    deadline = time.monotonic() + args.timeout_images
    project = call("GET", f"/projects/{pid}")
    while time.monotonic() < deadline:
        statuses = [scene["status"] for scene in project["scenes"]]
        print("   images:", ", ".join(statuses), flush=True)
        if all(status not in ("queued", "generating") for status in statuses):
            break
        time.sleep(10)
        project = call("GET", f"/projects/{pid}")
    bad = [(i + 1, s.get("status"), s.get("error")) for i, s in enumerate(project["scenes"])
           if s["status"] != "ready" or s.get("placeholder")]
    if bad:
        print("   IMAGE BLOCKED:", bad, flush=True)
        (OUT / "state.json").write_text(json.dumps({"project_id": pid, "stage": "images_blocked",
                                                    "scenes": [{k: s.get(k) for k in ("status", "error", "placeholder")}
                                                               for s in project["scenes"]]}, ensure_ascii=False, indent=2), encoding="utf-8")
        return 3
    for index, scene in enumerate(project["scenes"], 1):
        response = client.get(base + "/media/" + scene["image_path"], timeout=120)
        response.raise_for_status()
        (OUT / f"scene_{index}.png").write_bytes(response.content)
    print("   images saved to", OUT, flush=True)

    print("8. approve scenes", flush=True)
    for scene in project["scenes"]:
        call("POST", f"/projects/{pid}/scenes/{scene['id']}/approve")

    print(f"9. generate narration (provider={args.provider})", flush=True)
    project = call("POST", f"/projects/{pid}/audio/ai",
                   {"voice": args.voice, "speed": 1.0, "provider": args.provider}, timeout=420)
    audio = project.get("audio") or {}
    print("   audio duration:", audio.get("duration"), "provider:", audio.get("provider"),
          "caption_status:", audio.get("caption_status"), flush=True)

    print("10. render", flush=True)
    call("POST", f"/projects/{pid}/render")
    deadline = time.monotonic() + 900
    project = call("GET", f"/projects/{pid}")
    while time.monotonic() < deadline:
        render = project["render"]
        print("   render:", render.get("status"), render.get("progress"), flush=True)
        if render.get("status") in ("done", "failed"):
            break
        time.sleep(10)
        project = call("GET", f"/projects/{pid}")
    render = project["render"]
    if render.get("status") != "done":
        print("   RENDER FAILED:", render.get("message"), flush=True)
        return 4

    print("11. download MP4", flush=True)
    response = client.get(base + "/media/" + render["video_path"] + "?download=1", timeout=300)
    response.raise_for_status()
    video = OUT / "final.mp4"
    video.write_bytes(response.content)
    print("   saved:", video, len(response.content), "bytes", flush=True)
    (OUT / "state.json").write_text(json.dumps({
        "project_id": pid, "stage": "rendered", "language": args.language, "provider": args.provider,
        "audio": audio, "render": render, "video": str(video), "video_bytes": len(response.content),
        "caption_timing": [s.get("caption_timing") for s in project["scenes"]],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print("DRY RUN PASSED", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
