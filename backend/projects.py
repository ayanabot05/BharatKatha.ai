import os
import shutil
import asyncio
import hashlib
import json
import math
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel, Field

import ai
import render
import pulse
from core import db, current_user, now_iso, new_id, save_media, cached, get_object, log, CACHE

router = APIRouter(prefix="/api/projects")
_tasks = set()

def spawn(coro):
    t = asyncio.create_task(coro)
    _tasks.add(t)
    t.add_done_callback(_tasks.discard)


async def owned(pid, user):
    p = await db.projects.find_one({"id": pid, "user_id": user["id"]}, {"_id": 0})
    if not p:
        raise HTTPException(404, "Project not found")
    return p


async def upd(pid, **fields):
    fields["updated_at"] = now_iso()
    await db.projects.update_one({"id": pid}, {"$set": fields})


class ProjectIn(BaseModel):
    title: Optional[str] = None
    language: str = "te"
    region: str = "Andhra Pradesh"


class ProjectPatch(BaseModel):
    title: Optional[str] = None
    language: Optional[str] = None
    region: Optional[str] = None
    idea: Optional[str] = None
    style: Optional[str] = None
    step: Optional[int] = None
    captions_on: Optional[bool] = None
    script: Optional[dict] = None


class ScriptIn(BaseModel):
    idea: str = Field(min_length=3)
    language: str = "te"
    region: str = "Andhra Pradesh"
    duration: int = 45
    tone: str = "Emotional"


class EditIn(BaseModel):
    instruction: Optional[str] = None


class VoiceIn(BaseModel):
    voice: str = "fable"
    speed: float = Field(default=1.0, ge=0.75, le=1.25)


def review_fingerprint(project):
    content = {key: project.get(key) for key in ("script", "idea", "language", "region", "duration")}
    return hashlib.sha256(json.dumps(content, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def review_is_current(project):
    review = project.get("validation") or {}
    return review.get("all_passed") is True and review.get("content_fingerprint") == review_fingerprint(project)


def scenes_from_script(script, old=None):
    old = old or []
    out = []
    for i, s in enumerate(script.get("scenes", [])):
        candidate = old[i] if i < len(old) else {}
        # A rewritten visual cannot safely keep a picture from the earlier script.
        prev = candidate if candidate.get("visual") == s.get("visual", "") else {}
        out.append({"id": prev.get("id") or new_id(), "narration": s.get("narration", ""), "visual": s.get("visual", ""),
                    "beat": s.get("beat", ""), "image_path": prev.get("image_path"), "status": prev.get("status", "pending"),
                    "placeholder": prev.get("placeholder", False), "approved": prev.get("approved", False),
                    "versions": prev.get("versions", []), "audio_path": None, "audio_duration": None})
    return out


def script_with_scenes(script, scenes):
    if not script:
        return script
    updated = dict(script)
    updated["scenes"] = [{"narration": s["narration"], "visual": s["visual"], "beat": s.get("beat", "")}
                         for s in scenes]
    if scenes:
        updated["hook"] = scenes[0]["narration"]
        updated["ending"] = scenes[-1]["narration"]
    return updated


@router.post("")
async def create(body: ProjectIn, user=Depends(current_user)):
    p = {"id": new_id(), "user_id": user["id"], "title": body.title or "Untitled story", "language": body.language,
         "region": body.region, "idea": "", "script": None, "validation": None, "approved": False, "style": None,
         "scenes": [], "audio": None, "captions_on": True, "render": {"status": "idle", "progress": 0},
         "step": 1, "created_at": now_iso(), "updated_at": now_iso()}
    await db.projects.insert_one(dict(p))
    return p


@router.get("")
async def list_projects(user=Depends(current_user)):
    return await db.projects.find({"user_id": user["id"]}, {"_id": 0}).sort("updated_at", -1).to_list(200)


@router.get("/{pid}")
async def get_project(pid: str, user=Depends(current_user)):
    return await owned(pid, user)


@router.patch("/{pid}")
async def patch(pid: str, body: ProjectPatch, user=Depends(current_user)):
    p = await owned(pid, user)
    fields = body.model_dump(exclude_none=True)
    context_changed = any(key in fields and fields[key] != p.get(key) for key in ("language", "region", "idea"))
    if context_changed:
        if (p.get("render") or {}).get("status") == "rendering":
            raise HTTPException(409, "Wait for the current render to finish before changing the story")
        fields.update(validation=None, approved=False, audio=None, srt=None,
                      render={"status": "idle", "progress": 0})
    if "script" in fields:
        if (p.get("render") or {}).get("status") == "rendering":
            raise HTTPException(409, "Wait for the current render to finish before changing the script")
        fields["scenes"] = scenes_from_script(fields["script"], p.get("scenes"))
        fields["script"] = script_with_scenes(fields["script"], fields["scenes"])
        fields["approved"] = False
        fields["validation"] = None
        fields["audio"] = None
        fields["render"] = {"status": "idle", "progress": 0}
        # user manually edited the script — signal to pulse
        await pulse.log_event(user["id"], "script_edited", p.get("language", ""), p.get("region", ""),
                              hook=(fields["script"] or {}).get("hook", ""), project_id=pid)
    if "style" in fields and fields["style"] != p.get("style"):
        if (p.get("render") or {}).get("status") == "rendering":
            raise HTTPException(409, "Wait for the current render to finish before changing style")
        current_scenes = fields.get("scenes", p.get("scenes") or [])
        fields["scenes"] = [{**s, "image_path": None, "status": "pending", "placeholder": False,
                             "approved": False, "versions": [], "audio_path": None, "audio_duration": None} for s in current_scenes]
        fields["audio"] = None
        fields["render"] = {"status": "idle", "progress": 0}
    if fields:
        await upd(pid, **fields)
    return await owned(pid, user)


@router.delete("/{pid}")
async def delete(pid: str, user=Depends(current_user)):
    await owned(pid, user)
    await db.projects.delete_one({"id": pid})
    return {"ok": True}


# ---------- script ----------
@router.post("/{pid}/script/generate")
async def gen_script(pid: str, body: ScriptIn, user=Depends(current_user)):
    p = await owned(pid, user)
    if (p.get("render") or {}).get("status") == "rendering":
        raise HTTPException(409, "Wait for the current render to finish before making a new script")
    try:
        script = await ai.write_script(body.idea, body.language, body.region, body.duration, body.tone)
    except Exception as e:
        log.exception("script")
        raise HTTPException(502, f"Script generation failed: {e}")
    await upd(pid, idea=body.idea, language=body.language, region=body.region, duration=body.duration, tone=body.tone,
              script=script, scenes=scenes_from_script(script), title=script.get("title") or script.get("title_en") or "Untitled",
              validation=None, approved=False, audio=None, render={"status": "idle", "progress": 0}, step=2)
    await pulse.log_event(
        user["id"], "script_generated", body.language, body.region,
        genre=(script.get("category") or ""), hook=(script.get("hook") or ""),
        idea_title=(script.get("title_en") or script.get("title") or ""), project_id=pid,
    )
    return await owned(pid, user)


@router.post("/{pid}/script/validate")
async def validate(pid: str, user=Depends(current_user)):
    p = await owned(pid, user)
    if not p.get("script"):
        raise HTTPException(400, "Generate a script first")
    try:
        v = await ai.validate_script(p["script"], p["language"], p["region"], p.get("duration", 45), p.get("idea", ""))
    except Exception as e:
        raise HTTPException(502, f"Validation failed: {e}")
    v["content_fingerprint"] = review_fingerprint(p)
    await upd(pid, validation=v, approved=False)
    return await owned(pid, user)


@router.post("/{pid}/script/improve")
async def improve(pid: str, user=Depends(current_user)):
    p = await owned(pid, user)
    if (p.get("render") or {}).get("status") == "rendering":
        raise HTTPException(409, "Wait for the current render to finish before revising the script")
    if not p.get("validation"):
        raise HTTPException(400, "Run the Ram AI review first")
    fixes = {a["name"]: a.get("fixes", []) for a in p["validation"].get("agents", [])}
    for agent in p["validation"].get("agents", []):
        if agent.get("key") == "concept" and agent.get("misses"):
            fixes[agent["name"]] = fixes.get(agent["name"], []) + agent["misses"]
    if p["validation"].get("ram_ai_fixes"):
        fixes["Ram AI Hard Checks"] = p["validation"]["ram_ai_fixes"]
    try:
        script = await ai.write_script(p["idea"], p["language"], p["region"], p.get("duration", 45),
                                       p.get("tone", "Emotional"), feedback=fixes, previous=p["script"])
        v = await ai.validate_script(script, p["language"], p["region"], p.get("duration", 45), p.get("idea", ""))
    except Exception as e:
        raise HTTPException(502, f"Improve failed: {e}")
    v["content_fingerprint"] = review_fingerprint({**p, "script": script})
    await upd(pid, script=script, scenes=scenes_from_script(script, p.get("scenes")), validation=v,
              approved=False, audio=None, render={"status": "idle", "progress": 0})
    return await owned(pid, user)


@router.post("/{pid}/script/approve")
async def approve(pid: str, user=Depends(current_user)):
    p = await owned(pid, user)
    v = p.get("validation")
    if not v:
        raise HTTPException(400, "Run the Ram AI review before approving")
    if not v.get("safe"):
        raise HTTPException(400, "Ram AI Safety Guard flagged this script. Apply fixes first.")
    if not v.get("all_passed"):
        raise HTTPException(400, "Ram AI hard checks are incomplete. Apply fixes and review again before approving.")
    if not review_is_current(p):
        raise HTTPException(400, "This review belongs to an older script or idea. Run the review again.")
    await upd(pid, approved=True, step=max(p.get("step", 1), 3))
    await pulse.log_event(
        user["id"], "script_approved", p.get("language", ""), p.get("region", ""),
        hook=((p.get("script") or {}).get("hook") or ""), project_id=pid,
    )
    return await owned(pid, user)


@router.post("/{pid}/script/reject")
async def reject(pid: str, user=Depends(current_user)):
    """Explicit reject — this is what makes survive_rate meaningful in pulse."""
    p = await owned(pid, user)
    await upd(pid, approved=False)
    await pulse.log_event(
        user["id"], "script_rejected", p.get("language", ""), p.get("region", ""),
        hook=((p.get("script") or {}).get("hook") or ""), project_id=pid,
    )
    return await owned(pid, user)


# ---------- scenes ----------
async def _scene_job(pid, uid, sid, instruction=None, ref=None):
    """Returns (image_bytes, is_placeholder) on success, None on failure (scene is marked failed)."""
    p = await db.projects.find_one({"id": pid}, {"_id": 0})
    scene = next(s for s in p["scenes"] if s["id"] == sid)
    try:
        if instruction and scene.get("image_path") and not scene.get("placeholder"):
            # real image: edit it in place
            base = (await get_object(scene["image_path"]))[0]
            data, mime, placeholder = await ai.gen_image(ai.edit_prompt(p, instruction), [base])
        elif instruction:
            # no real image to edit (placeholder or none yet): regenerate the scene with the instruction applied
            edited = dict(scene, visual=f"{scene.get('visual', '')}. Also: {instruction}")
            data, mime, placeholder = await ai.gen_image(ai.scene_prompt(p, edited, bool(ref)), [ref] if ref else None)
        else:
            data, mime, placeholder = await ai.gen_image(ai.scene_prompt(p, scene, bool(ref)), [ref] if ref else None)
        path = await save_media(uid, "scenes", data, "png" if "png" in mime else "jpg", mime)
        await db.projects.update_one({"id": pid, "scenes.id": sid},
                                     {"$set": {"scenes.$.image_path": path, "scenes.$.status": "ready",
                                               "scenes.$.placeholder": placeholder, "scenes.$.approved": False,
                                               "scenes.$.error": "Placeholder image (Gemini quota). Not a real scene." if placeholder else None},
                                      "$push": {"scenes.$.versions": path}})
        return data, placeholder
    except Exception as e:
        log.exception("scene image")
        await db.projects.update_one({"id": pid, "scenes.id": sid},
                                     {"$set": {"scenes.$.status": "failed", "scenes.$.approved": False,
                                               "scenes.$.error": str(e)[:200]}})
        return None


def best_scene_reference(project, current, references):
    """Prefer the newest earlier image sharing the most named characters."""
    names = ai.scene_character_names(project, current)
    best, best_overlap = None, -1
    for previous, data in references:
        overlap = len(names & ai.scene_character_names(project, previous))
        if overlap >= best_overlap:
            best, best_overlap = data, overlap
    return best


async def _all_scenes_job(pid, uid, ids):
    first = await _scene_job(pid, uid, ids[0])
    if first:
        data, placeholder = first
        # Prefer the latest earlier image containing the same named characters.
        # A first-scene-only reference loses characters who enter later.
        project = await db.projects.find_one({"id": pid}, {"_id": 0})
        first_scene = next(s for s in project["scenes"] if s["id"] == ids[0])
        references = [] if placeholder else [(first_scene, data)]
        for sid in ids[1:]:
            current = next(s for s in project["scenes"] if s["id"] == sid)
            result = await _scene_job(pid, uid, sid, ref=best_scene_reference(project, current, references))
            if result and not result[1]:
                references.append((current, result[0]))
    else:
        p = await db.projects.find_one({"id": pid}, {"_id": 0})
        scenes = p.get("scenes") or []
        s1 = next((s for s in scenes if s["id"] == ids[0]), None)
        err = (s1.get("error") if s1 else None) or "Scene 1 generation failed"
        for sid in ids[1:]:
            await db.projects.update_one({"id": pid, "scenes.id": sid},
                                         {"$set": {"scenes.$.status": "failed", "scenes.$.error": err}})


async def mark_generating(pid, ids):
    row = await db.projects.find_one({"id": pid}, {"_id": 0})
    if not row:
        return
    scenes = row.get("scenes") or []
    id_set = set(ids)
    changed = False
    for sc in scenes:
        if sc.get("id") in id_set:
            sc["status"] = "generating"
            sc["error"] = None
            sc["approved"] = False
            changed = True
    if changed:
        await db.projects.update_one({"id": pid}, {"$set": {"scenes": scenes}})


@router.post("/{pid}/scenes/generate")
async def gen_scenes(pid: str, user=Depends(current_user)):
    p = await owned(pid, user)
    if not p.get("approved") or not p.get("style"):
        raise HTTPException(400, "Approve the script and choose a style first")
    if p.get("render", {}).get("status") == "rendering" or any(s.get("status") == "generating" for s in p["scenes"]):
        raise HTTPException(409, "Wait for the current generation or render to finish")
    ids = [s["id"] for s in p["scenes"]]
    if not ids:
        raise HTTPException(400, "Add a scene before generating pictures")
    await mark_generating(pid, ids)
    await upd(pid, step=max(p.get("step", 1), 4), render={"status": "idle", "progress": 0})
    spawn(_all_scenes_job(pid, user["id"], ids))
    return await owned(pid, user)


@router.post("/{pid}/scenes/{sid}/regenerate")
async def regen_scene(pid: str, sid: str, body: EditIn, user=Depends(current_user)):
    p = await owned(pid, user)
    if not any(s["id"] == sid for s in p["scenes"]):
        raise HTTPException(404, "Scene not found")
    if p.get("render", {}).get("status") == "rendering" or any(s.get("status") == "generating" for s in p["scenes"]):
        raise HTTPException(409, "Wait for the current generation or render to finish")
    ref = None
    # only real images make useful style references
    others = [s for s in p["scenes"] if s["id"] != sid and s.get("image_path") and not s.get("placeholder")]
    if others:
        ref = (await get_object(others[0]["image_path"]))[0]
    await mark_generating(pid, [sid])
    await upd(pid, render={"status": "idle", "progress": 0})
    spawn(_scene_job(pid, user["id"], sid, body.instruction, ref))
    await pulse.log_event(user["id"], "scene_regenerated", p.get("language", ""), p.get("region", ""), project_id=pid)
    return await owned(pid, user)


@router.post("/{pid}/scenes/{sid}/approve")
async def approve_scene(pid: str, sid: str, user=Depends(current_user)):
    p = await owned(pid, user)
    if p.get("render", {}).get("status") == "rendering":
        raise HTTPException(409, "Wait for the current render to finish")
    scene = next((s for s in p.get("scenes", []) if s["id"] == sid), None)
    if not scene:
        raise HTTPException(404, "Scene not found")
    if scene.get("status") != "ready" or not scene.get("image_path") or scene.get("placeholder"):
        raise HTTPException(400, "Generate a real scene image before approving it")
    await db.projects.update_one({"id": pid, "scenes.id": sid}, {"$set": {"scenes.$.approved": True}})
    await upd(pid, render={"status": "idle", "progress": 0})
    return await owned(pid, user)


class SceneTextIn(BaseModel):
    narration: Optional[str] = None
    visual: Optional[str] = None


@router.patch("/{pid}/scenes/{sid}")
async def patch_scene(pid: str, sid: str, body: SceneTextIn, user=Depends(current_user)):
    p = await owned(pid, user)
    scene = next((s for s in p.get("scenes", []) if s["id"] == sid), None)
    if not scene:
        raise HTTPException(404, "Scene not found")
    if p.get("render", {}).get("status") == "rendering" or scene.get("status") == "generating":
        raise HTTPException(409, "Wait for scene generation or rendering to finish")
    fields = {f"scenes.$.{k}": v.strip() for k, v in body.model_dump(exclude_none=True).items()}
    if any(not v for v in fields.values()):
        raise HTTPException(400, "Narration and visual description cannot be empty")
    if "scenes.$.visual" in fields and fields["scenes.$.visual"] != scene.get("visual"):
        fields.update({"scenes.$.image_path": None, "scenes.$.status": "pending",
                       "scenes.$.placeholder": False, "scenes.$.approved": False,
                       "scenes.$.versions": []})
    if "scenes.$.narration" in fields and fields["scenes.$.narration"] != scene.get("narration"):
        fields.update({"scenes.$.audio_path": None, "scenes.$.audio_duration": None})
        await upd(pid, audio=None)
    if fields:
        await upd(pid, render={"status": "idle", "progress": 0})
    await db.projects.update_one({"id": pid, "scenes.id": sid}, {"$set": fields})
    if fields:
        current = await owned(pid, user)
        await upd(pid, script=script_with_scenes(current.get("script"), current.get("scenes") or []),
                  validation=None, approved=False)
    return await owned(pid, user)


class SceneCreateIn(BaseModel):
    narration: str = Field(min_length=1, max_length=1000)
    visual: str = Field(min_length=1, max_length=2000)
    after_id: Optional[str] = None


@router.post("/{pid}/scenes")
async def add_scene(pid: str, body: SceneCreateIn, user=Depends(current_user)):
    p = await owned(pid, user)
    if p.get("render", {}).get("status") == "rendering" or any(s.get("status") == "generating" for s in p.get("scenes", [])):
        raise HTTPException(409, "Wait for current generation or rendering to finish")
    scenes = list(p.get("scenes") or [])
    if len(scenes) >= 12:
        raise HTTPException(400, "A video can have at most 12 scenes")
    if body.after_id and not any(s["id"] == body.after_id for s in scenes):
        raise HTTPException(404, "Previous scene not found")
    index = next((i + 1 for i, s in enumerate(scenes) if s["id"] == body.after_id), len(scenes))
    scenes.insert(index, {"id": new_id(), "narration": body.narration.strip(), "visual": body.visual.strip(),
                          "beat": "custom", "image_path": None, "status": "pending", "placeholder": False,
                          "approved": False, "versions": [], "audio_path": None, "audio_duration": None})
    await upd(pid, scenes=scenes, script=script_with_scenes(p.get("script"), scenes),
              validation=None, approved=False, audio=None,
              render={"status": "idle", "progress": 0})
    return await owned(pid, user)


class ThumbnailIn(BaseModel):
    scene_id: str
    title: str = Field(min_length=1, max_length=80)


@router.post("/{pid}/thumbnail")
async def make_thumbnail(pid: str, body: ThumbnailIn, user=Depends(current_user)):
    p = await owned(pid, user)
    scene = next((s for s in p.get("scenes", []) if s["id"] == body.scene_id), None)
    if not scene or not scene.get("image_path"):
        raise HTTPException(400, "Choose a scene with a picture")
    if scene.get("placeholder") or not scene.get("approved"):
        raise HTTPException(400, "Approve a real scene picture before making a thumbnail")
    path = await cached(scene["image_path"])
    data = await asyncio.to_thread(render.thumbnail_png, path, body.title, p["language"])
    media_path = await save_media(user["id"], "thumbnails", data, "png", "image/png")
    script = {**(p.get("script") or {}), "thumbnail_path": media_path, "thumbnail_scene_id": scene["id"],
              "thumbnail_title": body.title}
    await upd(pid, script=script)
    return await owned(pid, user)


@router.delete("/{pid}/scenes/{sid}")
async def remove_scene(pid: str, sid: str, user=Depends(current_user)):
    p = await owned(pid, user)
    scenes = p.get("scenes") or []
    if not any(s["id"] == sid for s in scenes):
        raise HTTPException(404, "Scene not found")
    if len(scenes) <= 1:
        raise HTTPException(400, "Keep at least one scene")
    if p.get("render", {}).get("status") == "rendering" or any(s.get("status") == "generating" for s in scenes):
        raise HTTPException(409, "Wait for current generation or rendering to finish")
    remaining = [s for s in scenes if s["id"] != sid]
    await upd(pid, scenes=remaining, script=script_with_scenes(p.get("script"), remaining),
              validation=None, approved=False, audio=None,
              render={"status": "idle", "progress": 0})
    return await owned(pid, user)


# ---------- audio ----------
@router.post("/{pid}/audio/ai")
async def audio_ai(pid: str, body: VoiceIn, user=Depends(current_user)):
    p = await owned(pid, user)
    if (p.get("render") or {}).get("status") == "rendering":
        raise HTTPException(409, "Wait for the render to finish before replacing narration")
    if not p["scenes"]:
        raise HTTPException(400, "No scenes")
    try:
        clips = await asyncio.gather(*[ai.tts_timed(s["narration"], body.voice, body.speed, p.get("language", "")) for s in p["scenes"]])
    except Exception as e:
        raise HTTPException(502, f"Voice generation failed: {e}")
    scenes, locals_ = p["scenes"], []
    for s, speech in zip(scenes, clips):
        data = speech["audio"]
        path = await save_media(user["id"], "audio", data, "mp3", "audio/mpeg")
        local = await cached(path)
        s["audio_path"], s["audio_duration"] = path, round(await asyncio.to_thread(render.duration, local), 2)
        if s["audio_duration"] <= 0:
            raise HTTPException(502, "Voice provider returned unreadable audio")
        s["audio_captions"] = render.timed_captions(speech["words"], s["audio_duration"]) if speech["words"] else []
        s["caption_timing"] = speech["timing_source"]
        locals_.append(local)
    combined = CACHE / f"combined_{pid}.mp3"
    await asyncio.to_thread(render.concat_audio, locals_, combined)
    path = await save_media(user["id"], "audio", combined.read_bytes(), "mp3", "audio/mpeg")
    current = await owned(pid, user)
    if review_fingerprint(current) != review_fingerprint(p) or (current.get("render") or {}).get("status") == "rendering":
        raise HTTPException(409, "The story changed while narration was generating. Generate it again for the current scenes.")
    # Preserve any image approvals or generation results that arrived while TTS ran.
    timing = {s["id"]: {k: s[k] for k in ("audio_path", "audio_duration", "audio_captions", "caption_timing")} for s in scenes}
    scenes = [{**s, **timing[s["id"]]} for s in current["scenes"]]
    await upd(pid, scenes=scenes, audio={"mode": "ai", "voice": body.voice, "speed": body.speed, "path": path,
                                         "duration": round(render.duration(combined), 2)},
              render={"status": "idle", "progress": 0}, srt=None, step=max(p.get("step", 1), 6))
    return await owned(pid, user)


@router.post("/{pid}/audio/upload")
async def audio_upload(pid: str, file: UploadFile = File(...), mode: str = "upload", user=Depends(current_user)):
    p = await owned(pid, user)
    if (p.get("render") or {}).get("status") == "rendering":
        raise HTTPException(409, "Wait for the render to finish before replacing narration")
    data = await file.read()
    if len(data) > 25 * 1024 * 1024:
        raise HTTPException(400, "Audio must be under 25 MB")
    try:
        mp3_bytes = await asyncio.to_thread(render.to_mp3_bytes, data)
    except Exception:
        raise HTTPException(400, "Could not read this audio file")
    dur = round(await asyncio.to_thread(render.duration_bytes, mp3_bytes), 2)
    if not math.isfinite(dur) or dur <= 0:
        raise HTTPException(400, "The audio file has no playable duration")
    path = await save_media(user["id"], "audio", mp3_bytes, "mp3", "audio/mpeg")
    await upd(pid, audio={"mode": "record" if mode == "record" else "upload", "path": path, "duration": dur,
                          "filename": file.filename}, render={"status": "idle", "progress": 0}, srt=None,
              step=max(p.get("step", 1), 6))
    return await owned(pid, user)


async def render_timeline(project, audio_local):
    scenes, audio = project["scenes"], project["audio"]
    total = audio["duration"]
    if not math.isfinite(total) or total <= 0:
        raise ValueError("Narration has no playable duration. Replace the audio.")
    caps, timing = [], "none"
    if audio["mode"] == "ai":
        durations = [s.get("audio_duration") or 0 for s in scenes]
        if any(d <= 0 or not math.isfinite(d) for d in durations):
            raise ValueError("Scene narration is incomplete. Generate narration again.")
        scale = total / sum(durations)
        offset = 0.0
        timing = "provider"
        for scene, d in zip(scenes, durations):
            if project.get("captions_on", True):
                local = scene.get("audio_captions")
                if not local:
                    local = render.chunk_captions(scene["narration"], d)
                    timing = "estimated"
                for cap in render.checked_captions(local, d):
                    caps.append({"text": cap["text"], "start": (offset + cap["start"]) * scale,
                                 "end": (offset + cap["end"]) * scale})
            offset += d
        durations = [d * scale for d in durations]
        if not project.get("captions_on", True):
            timing = "none"
    else:
        weights = [max(len(s["narration"]), 1) for s in scenes]
        durations = [total * w / sum(weights) for w in weights]
        if project.get("captions_on", True):
            try:
                caps = render.checked_captions(await ai.transcribe(audio_local, project["language"]), total)
            except Exception as exc:
                raise RuntimeError("Could not transcribe this recording. Retry later or turn off burn-in captions to render without subtitles.") from exc
            timing = "transcription"
    return render.frame_durations(durations), caps, timing


# ---------- render ----------
async def _render_job(pid, uid):
    p = await db.projects.find_one({"id": pid}, {"_id": 0})
    lang, scenes, audio = p["language"], p["scenes"], p["audio"]
    work = CACHE / f"render_{pid}_{new_id()}"
    work.mkdir()

    async def prog(pct, msg):
        await upd(pid, render={"status": "rendering", "progress": pct, "message": msg})
    try:
        await prog(5, "Preparing narration")
        audio_local = await cached(audio["path"])
        await prog(10, "Preparing caption timing")
        durs, caps_all, caption_timing = await render_timeline(p, audio_local)
        clips, t0 = [], 0.0
        for i, (s, d) in enumerate(zip(scenes, durs)):
            await prog(15 + int(70 * i / len(scenes)), f"Animating scene {i + 1} of {len(scenes)}")
            img = work / f"img_{i}.jpg"
            render.prep_image(await cached(s["image_path"]), img)
            local_caps = []
            if p.get("captions_on", True):
                for c in caps_all:
                    a, b = max(c["start"], t0), min(c["end"], t0 + d)
                    if b - a > 0.15:
                        local_caps.append({"text": c["text"], "start": a - t0, "end": b - t0})
            out = work / f"clip_{i}.mp4"
            await asyncio.to_thread(render.scene_clip, img, d, local_caps, lang, out, i, work)
            clips.append(out)
            t0 += d
        await prog(90, "Mixing voice + video")
        final = work / "final.mp4"
        await asyncio.to_thread(render.mux, clips, audio_local, final, work)
        path = await save_media(uid, "videos", final.read_bytes(), "mp4", "video/mp4")
        await upd(pid, render={"status": "done", "progress": 100, "message": "Your video is ready", "video_path": path,
                               "duration": round(render.duration(final), 2), "rendered_at": now_iso(),
                               "caption_timing": caption_timing,
                               "scene_timing": "narration" if audio["mode"] == "ai" else "estimated",
                               "srt": render.srt(caps_all)},
                  srt=render.srt(caps_all), step=6)
        await pulse.log_event(uid, "render_done", lang, p.get("region", ""), project_id=pid,
                              meta={"duration": round(render.duration(final), 2)})
    except Exception as e:
        log.exception("render")
        await upd(pid, render={"status": "failed", "progress": 0, "message": str(e)[:300]})
    finally:
        shutil.rmtree(work, ignore_errors=True)


@router.post("/{pid}/render")
async def start_render(pid: str, user=Depends(current_user)):
    p = await owned(pid, user)
    if not p.get("approved") or not review_is_current(p):
        raise HTTPException(400, "Review and approve the current script before rendering")
    if not p.get("audio"):
        raise HTTPException(400, "Add a voice-over first")
    if not p["scenes"] or any(s.get("status") != "ready" or not s.get("image_path") for s in p["scenes"]):
        raise HTTPException(400, "All scene images must be ready")
    fakes = [i + 1 for i, s in enumerate(p["scenes"]) if s.get("placeholder")]
    if fakes:
        raise HTTPException(400, f"Scene(s) {', '.join(map(str, fakes))} are placeholders, not real images. "
                                 "Fix the image quota and regenerate them before rendering.")
    unapproved = [i + 1 for i, s in enumerate(p["scenes"]) if not s.get("approved")]
    if unapproved:
        raise HTTPException(400, f"Review and approve scene(s) {', '.join(map(str, unapproved))} before rendering.")
    if p.get("render", {}).get("status") == "rendering":
        raise HTTPException(409, "Already rendering")
    await upd(pid, render={"status": "rendering", "progress": 1, "message": "Queued"})
    spawn(_render_job(pid, user["id"]))
    return await owned(pid, user)
