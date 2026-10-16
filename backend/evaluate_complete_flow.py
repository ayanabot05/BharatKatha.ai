"""Exercise an approved benchmark story through real images, narration and MP4.

Use --stage prepare to generate and save scene previews for visual inspection.
Use --stage render after reviewing the previews. All providers use backend config.
"""
import argparse
import json
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "test_reports" / "complete_flow_case7"
STATE = OUT / "state.json"
CASE = 7


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=("prepare", "fix-images", "refresh-audio", "render", "status"), required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--start-image", type=int, default=1)
    parser.add_argument("--only-images", help="Comma-separated one-based image numbers")
    args = parser.parse_args()
    load_dotenv(Path(__file__).with_name(".env"))
    OUT.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    base = args.base_url.rstrip("/") + "/api"

    def call(method, path, body=None, timeout=180):
        response = session.request(method, base + path, json=body, timeout=timeout)
        if not response.ok:
            raise RuntimeError(f"{method} {path}: HTTP {response.status_code}")
        return response.json()

    call("POST", "/auth/login", {"email": os.environ["ADMIN_EMAIL"], "password": os.environ["ADMIN_PASSWORD"]})
    if args.stage == "status":
        state = json.loads(STATE.read_text(encoding="utf-8"))
        p = call("GET", f"/projects/{state['project_id']}")
        print(json.dumps({"approved": p.get("approved"), "validation": p.get("validation", {}).get("all_passed"),
                          "images": [{"status": s.get("status"), "error": s.get("error"),
                                      "versions": len(s.get("versions") or [])} for s in p["scenes"]],
                          "audio": bool(p.get("audio")), "render": p.get("render", {}).get("status")}, indent=2))
        return
    if args.stage == "prepare":
        report = json.loads((ROOT / "test_reports" / "script_fidelity_benchmark_2026-10-14_fullflow.json").read_text(encoding="utf-8"))
        item = next(entry for entry in report["cases"] if entry["case"] == CASE)
        if not item.get("script"):
            raise RuntimeError("Benchmark did not produce a story script")
        script = item["script"]
        # The benchmark stores only title and scenes; other fields are optional
        # for review and rendering. Keep the original idea in project context.
        existing = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
        if existing.get("stage") == "created":
            state = existing
            pid = state["project_id"]
            call("PATCH", f"/projects/{pid}", {"script": script})
        else:
            pid = call("POST", "/projects", {"title": "EVALUATION: repaired kite", "language": item["language"],
                                              "region": item["region"]})["id"]
            state = {"project_id": pid, "idea": item["idea"], "stage": "created", "images": []}
            STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
            call("PATCH", f"/projects/{pid}", {"idea": item["idea"], "duration": 35})
            call("PATCH", f"/projects/{pid}", {"script": script})
        for review_attempt in range(3):
            try:
                p = call("POST", f"/projects/{pid}/script/validate")
                break
            except RuntimeError as exc:
                if review_attempt == 2 or "HTTP 502" not in str(exc):
                    raise
                time.sleep(3)
        state["validation"] = {k: p["validation"].get(k) for k in ("overall", "all_passed", "content_aligned", "content_gaps")}
        STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        if not p["validation"].get("all_passed"):
            raise RuntimeError("The live project review blocked the saved benchmark story")
        call("POST", f"/projects/{pid}/script/approve")
        call("PATCH", f"/projects/{pid}", {"style": "storybook"})
        call("POST", f"/projects/{pid}/scenes/generate")
        deadline = time.monotonic() + 900
        while time.monotonic() < deadline:
            p = call("GET", f"/projects/{pid}")
            statuses = [scene["status"] for scene in p["scenes"]]
            print("Images:", ", ".join(statuses), flush=True)
            if all(status not in ("queued", "generating") for status in statuses):
                break
            time.sleep(10)
        if any(scene["status"] != "ready" or scene.get("placeholder") for scene in p["scenes"]):
            raise RuntimeError(f"Real image generation incomplete: {[scene['status'] for scene in p['scenes']]}")
        for index, scene in enumerate(p["scenes"], 1):
            response = session.get(base + "/media/" + scene["image_path"], timeout=60)
            response.raise_for_status()
            path = OUT / f"scene_{index}.png"
            path.write_bytes(response.content)
            state["images"].append({"scene": index, "path": str(path), "visual": scene["visual"]})
        STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        p = call("POST", f"/projects/{pid}/audio/ai", {"voice": "coral", "speed": 1.0}, timeout=300)
        state["audio_duration"] = p["audio"]["duration"]
        state["caption_timing"] = [scene.get("caption_timing") for scene in p["scenes"]]
        state["stage"] = "images_and_audio_ready"
        STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Prepared {pid}; inspect images in {OUT}", flush=True)
        return

    state = json.loads(STATE.read_text(encoding="utf-8"))
    if state.get("stage") not in ("images_and_audio_ready", "rendered"):
        raise RuntimeError("Run --stage prepare and inspect each image before rendering")
    pid = state["project_id"]
    p = call("GET", f"/projects/{pid}")
    if args.stage == "refresh-audio":
        p = call("POST", f"/projects/{pid}/audio/ai", {"voice": "coral", "speed": 1.0}, timeout=300)
        state["audio_duration"] = p["audio"]["duration"]
        state["caption_timing"] = [scene.get("caption_timing") for scene in p["scenes"]]
        state["stage"] = "images_and_audio_ready"
        STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"audio_duration": state["audio_duration"],
                          "caption_timing": state["caption_timing"]}, indent=2), flush=True)
        return
    if args.stage == "fix-images":
        instructions = [
            "Show the original torn red kite with bare ripped paper only. Remove EVERY white patch, tape strip, and repair mark. Grandma and boy may inspect it, but no repair has started. Keep Grandma's purple sari and the boy's blue shirt.",
            "The red kite remains torn and completely unpatched. Grandma points to the tear to teach the boy; she has not attached anything yet. Remove EVERY white patch and tape strip. Keep her purple sari and his blue shirt.",
            "This is the first repair action. Show the BOY'S blue-sleeved hand firmly PRESSING exactly ONE white paper patch onto the red kite so the patch is already partly ADHERED across the tear with visible glue contact. The patch must touch the kite surface, not hover above an open hole. Grandma only points and guides. No older patches or tape.",
            "The SAME red kite flies with exactly ONE narrow white paper patch on the RIGHT side of the kite's vertical bamboo center spar, matching the final sky shot. Remove the extra white rectangle on the LEFT side of the spar. The kite is otherwise red and intact. Grandma wears the SAME purple sari from the courtyard shots, and the boy wears the SAME blue shirt.",
            "One coherent single landscape and ONE horizon only. Remove the duplicated second horizon and repeated temple at the bottom of the image. The same red kite flies high with one completed white patch matching the prior shot. At the bottom edge Grandma's clothing is a purple sari with gold border, and the boy wears blue. Keep all subjects natural in one continuous scene, not stacked panels.",
        ]
        selected = {int(value) for value in args.only_images.split(",")} if args.only_images else None
        for index, (scene, instruction) in enumerate(zip(p["scenes"], instructions), 1):
            if index < args.start_image or (selected is not None and index not in selected):
                continue
            call("POST", f"/projects/{pid}/scenes/{scene['id']}/regenerate", {"instruction": instruction})
            deadline = time.monotonic() + 180
            while time.monotonic() < deadline:
                p = call("GET", f"/projects/{pid}")
                current = p["scenes"][index - 1]
                print(f"Image {index}: {current['status']}", flush=True)
                if current["status"] != "generating":
                    break
                time.sleep(8)
            if current["status"] != "ready" or current.get("placeholder"):
                raise RuntimeError(f"Image {index} could not be corrected: {current.get('error')}")
            response = session.get(base + "/media/" + current["image_path"], timeout=60)
            response.raise_for_status()
            (OUT / f"scene_{index}.png").write_bytes(response.content)
        state["stage"] = "images_and_audio_ready"
        STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        print("Corrected image previews saved; inspect before --stage render", flush=True)
        return
    for scene in p["scenes"]:
        call("POST", f"/projects/{pid}/scenes/{scene['id']}/approve")
    call("POST", f"/projects/{pid}/render")
    deadline = time.monotonic() + 600
    while time.monotonic() < deadline:
        p = call("GET", f"/projects/{pid}")
        render = p["render"]
        print("Render:", render.get("status"), render.get("progress"), flush=True)
        if render.get("status") in ("done", "failed"):
            break
        time.sleep(10)
    if render.get("status") != "done":
        raise RuntimeError(f"Render incomplete: {render.get('message')}")
    response = session.get(base + "/media/" + render["video_path"], timeout=180)
    response.raise_for_status()
    output = OUT / "final.mp4"
    output.write_bytes(response.content)
    state.update({"stage": "rendered", "video": str(output), "render": render})
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Rendered {output}", flush=True)


if __name__ == "__main__":
    main()
