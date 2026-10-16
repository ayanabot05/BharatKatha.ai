"""Generate queued scenes after verifying project ownership and job state."""

import asyncio
import os


async def main():
    from db_supabase import active_scene_token
    from core import db
    from projects import (_all_scenes_job, _single_scene_job, best_scene_reference,
                          mark_scene_status)
    from core import get_object

    pid = os.environ["SCENE_PROJECT_ID"]
    uid = os.environ["SCENE_USER_ID"]
    sid = os.environ.get("SCENE_ID", "")
    token = os.environ["SCENE_LEASE_TOKEN"]
    project = await db.projects.find_one({"id": pid, "user_id": uid}, {"_id": 0})
    if not project or project.get("scene_job_token") != token or not project.get("approved") or not project.get("style"):
        raise RuntimeError("Scene request is missing, stale or owned by another user")
    context = active_scene_token.set(token)
    try:
        if sid:
            scene = next((s for s in project["scenes"] if s["id"] == sid), None)
            if not scene or scene.get("status") != "queued":
                raise RuntimeError("Single scene request is no longer queued")
            index = project["scenes"].index(scene)
            earlier = [s for s in project["scenes"][:index] if s.get("image_path") and not s.get("placeholder")]
            references = [(s, (await get_object(s["image_path"]))[0]) for s in earlier]
            ref = best_scene_reference(project, scene, references) if references else None
            await mark_scene_status(pid, [sid], "generating")
            await _single_scene_job(pid, uid, sid, scene.get("pending_instruction"), ref)
            await db.projects.update_one({"id": pid, "scenes.id": sid},
                                         {"$set": {"scenes.$.pending_instruction": None}})
        else:
            ids = [s["id"] for s in project["scenes"] if s.get("status") == "queued"]
            if not ids:
                raise RuntimeError("Scene batch is no longer queued")
            await _all_scenes_job(pid, uid, ids)
    finally:
        try:
            latest = await db.projects.find_one({"id": pid, "user_id": uid}, {"_id": 0})
            if latest and latest.get("scene_job_token") == token:
                still_active = [s["id"] for s in latest.get("scenes", [])
                                if s.get("status") in {"queued", "generating"}]
                if still_active:
                    await mark_scene_status(pid, still_active, "pending")
            await db.projects.release_scene_job(pid, uid, token)
        finally:
            active_scene_token.reset(context)


if __name__ == "__main__":
    asyncio.run(main())
