"""Isolated local PostgreSQL probe for migration and durable job claim SQL.

Requires BHARATKATHA_PG_TEST_URL with a loopback host; refuses remote databases.
The minimal projects table mirrors the columns touched by the production claims.
"""

import asyncio
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

import psycopg2
from psycopg2.extras import Json

sys.path.insert(0, str(Path(__file__).parents[1]))
from db_supabase import SupabaseDB, active_render_token, active_scene_token


async def probe(url):
    db = SupabaseDB(url)
    with psycopg2.connect(url) as conn:
        with conn.cursor() as cur:
            cur.execute("""CREATE TABLE projects (
                id text PRIMARY KEY, user_id text NOT NULL, scenes jsonb NOT NULL,
                render jsonb NOT NULL, updated_at timestamptz DEFAULT NOW())""")
            cur.execute((Path(__file__).parents[1] / "migrations" / "002_cloud_scene_job.sql").read_text())
            cur.execute("""INSERT INTO projects (id,user_id,scenes,render) VALUES (%s,%s,%s,%s)""",
                        ("p1", "u1", Json([{"id": "s1", "status": "pending"}]), Json({"status": "idle"})))
    try:
        claims = await asyncio.gather(db.projects.claim_scene_job("p1", "u1", "lease-a"),
                                      db.projects.claim_scene_job("p1", "u1", "lease-b"))
        assert claims.count(True) == 1, f"atomic scene claim failed: {claims}"
        winner = "lease-a" if claims[0] else "lease-b"
        await db.projects.release_scene_job("p1", "u1", "wrong-token")
        row = await db.execute("SELECT scene_job_token FROM projects WHERE id='p1'", fetchone=True)
        assert row["scene_job_token"] == winner, "wrong token released active lease"
        await db.projects.release_scene_job("p1", "u1", winner)
        assert await db.projects.claim_scene_job("p1", "u1", "lease-old")
        await db.execute("UPDATE projects SET scene_job_started_at = NOW() - INTERVAL '26 minutes' WHERE id='p1'")
        assert await db.projects.claim_scene_job("p1", "u1", "lease-new"), "expired lease was not recoverable"
        await db.projects.release_scene_job("p1", "u1", "lease-old")
        row = await db.execute("SELECT scene_job_token FROM projects WHERE id='p1'", fetchone=True)
        assert row["scene_job_token"] == "lease-new", "old job released new lease"
        await db.projects.release_scene_job("p1", "u1", "lease-new")
        assert not await db.projects.claim_scene_job("p1", "other-user", "wrong-owner")
        assert await db.projects.claim_scene_job("p1", "u1", "expired-before-render")
        await db.execute("UPDATE projects SET scene_job_started_at = NOW() - INTERVAL '26 minutes' WHERE id='p1'")
        renders = await asyncio.gather(db.projects.claim_render_job("p1", "u1", "render-a", "2026-10-16T00:00:00+00:00"),
                                       db.projects.claim_render_job("p1", "u1", "render-b", "2026-10-16T00:00:00+00:00"))
        assert renders.count(True) == 1, f"atomic render claim failed: {renders}"
        lease_row = await db.execute("SELECT scene_job_token FROM projects WHERE id='p1'", fetchone=True)
        assert lease_row["scene_job_token"] is None, "render did not clear expired scene lease"
        rwinner = "render-a" if renders[0] else "render-b"
        stale_render = active_render_token.set("render-old")
        try:
            await db.projects.update_one({"id": "p1"}, {"$set": {"render": {"status": "done"}}})
        finally:
            active_render_token.reset(stale_render)
        row = await db.execute("SELECT render FROM projects WHERE id='p1'", fetchone=True)
        assert row["render"]["claim_token"] == rwinner, "stale render worker overwrote newer claim"
        await db.projects.fail_render_claim("p1", "u1", "wrong-token")
        row = await db.execute("SELECT render FROM projects WHERE id='p1'", fetchone=True)
        assert row["render"]["claim_token"] == rwinner, "wrong render token changed state"
        await db.projects.fail_render_claim("p1", "u1", rwinner)
        assert await db.projects.claim_scene_job("p1", "u1", "scene-current")
        stale_scene = active_scene_token.set("scene-old")
        try:
            await db.projects.update_one({"id": "p1", "scenes.id": "s1"},
                                         {"$set": {"scenes.$.status": "ready", "scenes.$.image_path": "stale.jpg"}})
        finally:
            active_scene_token.reset(stale_scene)
        row = await db.execute("SELECT scenes FROM projects WHERE id='p1'", fetchone=True)
        assert row["scenes"][0]["status"] == "pending", "stale scene worker overwrote newer claim"
        await db.projects.release_scene_job("p1", "u1", "scene-current")
        assert await db.projects.claim_scene_job("p1", "u1", "crashed-scene")
        await db.execute("UPDATE projects SET scenes = %s, scene_job_started_at = NOW() - INTERVAL '26 minutes' WHERE id='p1'",
                         (Json([{"id": "s1", "status": "generating"}]),))
        assert await db.projects.recover_expired_scene_job("p1", "u1", "crashed-scene")
        row = await db.execute("SELECT scenes, scene_job_token FROM projects WHERE id='p1'", fetchone=True)
        assert row["scene_job_token"] is None and row["scenes"][0]["status"] == "failed", "crashed scene was not recovered"
        print("PASS: migration SQL, atomic scene/render claims, owner guard, lease expiry and token-safe recovery")
    finally:
        with psycopg2.connect(url) as conn:
            with conn.cursor() as cur:
                cur.execute("DROP TABLE IF EXISTS projects")


if __name__ == "__main__":
    test_url = sys.argv[1] if len(sys.argv) > 1 else os.environ["BHARATKATHA_PG_TEST_URL"]
    if urlparse(test_url).hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise SystemExit("Refusing to run against a non-local database")
    asyncio.run(probe(test_url))
