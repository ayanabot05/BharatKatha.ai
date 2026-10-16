"""Entry point for one Cloud Run Job execution using the existing FFmpeg renderer."""

import asyncio
import os


async def main():
    from db_supabase import active_render_token
    from core import db
    from projects import _render_job

    pid = os.environ["RENDER_PROJECT_ID"]
    uid = os.environ["RENDER_USER_ID"]
    token = os.environ["RENDER_CLAIM_TOKEN"]
    project = await db.projects.find_one({"id": pid, "user_id": uid}, {"_id": 0})
    if not project or (project.get("render") or {}).get("status") != "rendering" or (project.get("render") or {}).get("claim_token") != token:
        raise RuntimeError("Render request is missing, stale or owned by another user")
    context = active_render_token.set(token)
    try:
        await _render_job(pid, uid)
    finally:
        active_render_token.reset(context)
    result = await db.projects.find_one({"id": pid, "user_id": uid}, {"render": 1})
    if not result or (result.get("render") or {}).get("status") != "done":
        raise RuntimeError("Cloud render did not complete")


if __name__ == "__main__":
    asyncio.run(main())
