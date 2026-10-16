"""One bounded real-provider test, executed only inside Cloud Run Jobs.

Uses a new evaluation project, never modifies an existing creator project.
"""
import asyncio
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

if not os.environ.get("CLOUD_RUN_JOB"):
    raise SystemExit("Run this test as a Cloud Run Job, not on the laptop")
required = {"DATABASE_URL", "TEST_USER_EMAIL", "GCS_BUCKET"}
if any(not os.environ.get(key) for key in required):
    raise SystemExit("Cloud test configuration is missing a required value")
# This job invokes project functions directly, never serves auth endpoints.
os.environ.setdefault("JWT_SECRET", "cloud-job-only-no-public-auth")
os.environ.update(TEXT_PROVIDER="vertex", IMAGE_PROVIDER="vertex", TTS_PROVIDER="google_chirp",
                  ALLOW_IMAGE_FALLBACK="false", PLACEHOLDER_USE_SAMPLES="false",
                  GOOGLE_CLOUD_PROJECT="ayana-video-studio", GOOGLE_CLOUD_LOCATION="global",
                  GOOGLE_SPEECH_LOCATION="global", GOOGLE_SPEECH_MODEL="long", PERSONALIZED_HOOKS="false")

import projects
from core import db, get_object
from google.cloud import storage
import render
import json

execution = re.sub(r"[^a-zA-Z0-9_-]", "-", os.environ.get("CLOUD_RUN_EXECUTION", "manual"))
PREFIX = f"fresh-video-test-20261015/{execution}"
report = {"test": PREFIX, "cloud_run_job": os.environ["CLOUD_RUN_JOB"],
          "started_at": datetime.now(timezone.utc).isoformat(), "checks": [], "status": "running"}


def save_report():
    storage.Client().bucket(os.environ["GCS_BUCKET"]).blob(f"{PREFIX}/report.json").upload_from_string(
        json.dumps(report, ensure_ascii=False, indent=2), content_type="application/json")


def stage(name):
    report["stage"] = name
    print(json.dumps({"stage": name, "project_id": report.get("project_id")}), flush=True)
    save_report()


async def settle(pid, user, kind, timeout=1200):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        p = await projects.owned(pid, user)
        if kind == "images" and not any(s["status"] in ("generating", "queued") for s in p["scenes"]):
            if any(s["status"] != "ready" or s.get("placeholder") for s in p["scenes"]):
                raise RuntimeError("Image generation failed: " + str([s.get("error") for s in p["scenes"]]))
            return p
        if kind == "render" and p["render"]["status"] in ("done", "failed"):
            if p["render"]["status"] != "done":
                raise RuntimeError("Render failed: " + str(p["render"].get("message")))
            return p
        await asyncio.sleep(5)
    raise RuntimeError(f"Timed out waiting for {kind}")


async def main():
    user = await db.users.find_one({"email": os.environ["TEST_USER_EMAIL"]})
    if not user:
        raise RuntimeError("Evaluation account unavailable")
    p = await projects.create(projects.ProjectIn(title="CLOUD TEST: caring for a sapling", language="te", region="Andhra Pradesh"), user)
    pid = p["id"]
    report["project_id"] = pid
    stage("fresh_script")
    p = await projects.gen_script(pid, projects.ScriptIn(
        idea="In a village courtyard, a grandmother and her granddaughter plant a small mango sapling together. The girl gently waters its roots with a small clay pot. The grandmother shows her how to keep the soil moist without flooding it. The next morning the girl returns and waters the SAME small sapling with care. End with the earned lesson that daily care helps life grow. No magic, no instant-grown tree, no time jump beyond the next morning.",
        language="te", region="Andhra Pradesh", duration=30, tone="Warm", category="Moral stories", audience="Families", platform="YouTube Shorts"), user)
    stage("script_review")
    p = await projects.validate(pid, user)
    if not p["validation"].get("all_passed"):
        p = await projects.improve(pid, user)
    if not (p.get("validation") or {}).get("all_passed"):
        report["review"] = p.get("validation")
        raise RuntimeError("Story review did not pass; approval was not bypassed")
    report["initial_review"] = p["validation"]
    await projects.approve(pid, user)
    await projects.patch(pid, projects.ProjectPatch(style="storybook"), user)
    stage("sequential_images")
    await projects.gen_scenes(pid, user)
    p = await settle(pid, user, "images")
    report["scene_count"] = len(p["scenes"])
    report["original_first_image"] = p["scenes"][0]["image_path"]
    stage("natural_bird_edit")
    instruction = "Add one small sparrow naturally in the distant courtyard background, perched on an existing branch or ledge. Match the scene's painted style, scale, perspective, warm light and shadows. Feet must grip its perch; no pasted-on edges or oversized bird. Preserve the grandmother, girl, sapling and their current actions. This is background wildlife, not a new story action."
    await projects.regen_scene(pid, p["scenes"][0]["id"], projects.EditIn(instruction=instruction), user)
    p = await settle(pid, user, "images")
    assert instruction in p["scenes"][0]["visual"]
    assert p["approved"] is False
    assert all(not s.get("approved") for s in p["scenes"])
    report["checks"].append("Image edit persisted; script and picture approvals invalidated")
    stage("review_after_edit")
    p = await projects.validate(pid, user)
    if not p["validation"].get("all_passed"):
        report["review"] = p["validation"]
        raise RuntimeError("Updated story review blocked the edit; no approval bypass")
    report["review_after_edit"] = p["validation"]
    await projects.approve(pid, user)
    for scene in p["scenes"]:
        await projects.approve_scene(pid, scene["id"], user)
    p = await projects.owned(pid, user)
    if not all(scene.get("approved") for scene in p["scenes"]):
        raise RuntimeError("A revised picture did not pass approval")
    report["checks"].append("All revised pictures approved in story order")
    stage("fresh_voice_and_captions")
    p = await projects.audio_ai(pid, projects.VoiceIn(voice="coral", speed=1.0, provider="google_chirp"), user)
    report["audio_duration"] = p["audio"]["duration"]
    report["caption_timing"] = [s.get("caption_timing") for s in p["scenes"]]
    if not all(source == "cloud_stt" and scene.get("audio_captions")
               for source, scene in zip(report["caption_timing"], p["scenes"])):
        raise RuntimeError("Cloud word timing or scene captions are missing")
    report["checks"].append("Cloud speech word timing and captions present for every scene")
    stage("cloud_render")
    await projects.start_render(pid, user)
    p = await settle(pid, user, "render")
    report["render"] = p["render"]
    report["script"] = p["script"]
    report["scenes"] = [{k: s.get(k) for k in ("id", "narration", "visual", "image_path", "audio_duration", "audio_captions")} for s in p["scenes"]]
    video = Path("/tmp/test-final.mp4")
    video.write_bytes((await get_object(p["render"]["video_path"]))[0])
    duration = render.duration(video)
    report["video_duration"] = duration
    report["duration_difference"] = abs(duration - p["audio"]["duration"])
    if report["duration_difference"] > .2:
        raise RuntimeError("Video and narration duration differ by more than 0.2 seconds")
    report["checks"].append("Rendered video and voice durations differ by at most 0.2 seconds")
    report["video_gcs_uri"] = f"gs://{os.environ['GCS_BUCKET']}/{p['render']['video_path']}"
    for second in [1, max(1, duration / 2), max(1, duration - 1)]:
        frame = Path(f"/tmp/frame-{second:.1f}.png")
        render.run(["-ss", str(second), "-i", str(video), "-frames:v", "1", str(frame)])
        storage.Client().bucket(os.environ["GCS_BUCKET"]).blob(f"{PREFIX}/{frame.name}").upload_from_filename(str(frame))
    report["status"] = "automated_checks_passed_manual_media_review_pending"
    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    stage("finished")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as exc:
        report["status"] = "failed"
        report["error"] = str(exc)[:1000]
        save_report()
        print(json.dumps({"status": "failed", "stage": report.get("stage"), "error_type": type(exc).__name__}), flush=True)
        raise SystemExit(1)
