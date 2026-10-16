"""Supabase PostgreSQL adapter for VidBharat. Includes the pulse_events collection."""
import os
import json
import asyncio
from contextvars import ContextVar
import logging
from typing import Any, Dict, List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor, Json

log = logging.getLogger("vidbharat.db")
active_scene_token = ContextVar("active_scene_token", default=None)
active_render_token = ContextVar("active_render_token", default=None)


def _parse_json(val):
    if val is None or isinstance(val, (dict, list)):
        return val
    if isinstance(val, str):
        try:
            return json.loads(val)
        except Exception:
            return val
    return val


def _clean_project(row):
    if not row:
        return None
    res = dict(row)
    for col in ("script", "validation", "scenes", "audio", "render", "brief", "content_contract"):
        if col in res:
            res[col] = _parse_json(res[col])
    if res.get("scenes") is None:
        res["scenes"] = []
    if "duration" not in res or res["duration"] is None:
        res["duration"] = 45
    if "tone" not in res or not res["tone"]:
        res["tone"] = "Emotional"
    return res


def _clean_coach(row):
    if not row:
        return None
    res = dict(row)
    for col in ("input", "report"):
        if col in res:
            res[col] = _parse_json(res[col])
    return res


from psycopg2.pool import ThreadedConnectionPool
import time

class SupabaseDB:
    def __init__(self, db_url: str):
        self.db_url = db_url
        url = self.db_url
        if ":6543" in url:
            url = url.replace(":6543", ":5432")
        self._clean_url = url
        self._pool = None
        self._init_pool()

    def _init_pool(self):
        try:
            self._pool = ThreadedConnectionPool(minconn=1, maxconn=10, dsn=self._clean_url, connect_timeout=10)
        except Exception as e:
            log.warning("Connection pool initialization: %s", e)
            self._pool = None

    def _get_conn(self):
        if self._pool is None:
            self._init_pool()
        if self._pool:
            try:
                conn = self._pool.getconn()
                if conn.closed:
                    self._pool.putconn(conn, close=True)
                    conn = self._pool.getconn()
                return conn
            except Exception as e:
                log.warning("Pool getconn error: %s", e)
        return psycopg2.connect(self._clean_url, connect_timeout=10)

    def _release_conn(self, conn, close=False):
        if self._pool and conn:
            try:
                self._pool.putconn(conn, close=close)
                return
            except Exception:
                pass
        if conn and not conn.closed:
            try:
                conn.close()
            except Exception:
                pass

    def _execute(self, query, params=(), fetchone=False, fetchall=False, commit=True):
        last_exc = None
        for attempt in range(3):
            conn = None
            try:
                conn = self._get_conn()
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(query, params)
                    res = cur.fetchone() if fetchone else (cur.fetchall() if fetchall else None)
                if commit:
                    conn.commit()
                self._release_conn(conn)
                return res
            except psycopg2.OperationalError as e:
                last_exc = e
                log.warning("OperationalError on attempt %d: %s. Retrying...", attempt + 1, e)
                if conn:
                    try:
                        conn.rollback()
                    except Exception:
                        pass
                    self._release_conn(conn, close=True)
                # Re-initialize pool if broken
                if attempt == 1:
                    try:
                        if self._pool:
                            self._pool.closeall()
                    except Exception:
                        pass
                    self._init_pool()
                time.sleep(0.4 * (attempt + 1))
            except Exception:
                if conn:
                    try:
                        conn.rollback()
                    except Exception:
                        pass
                    self._release_conn(conn)
                raise
        raise last_exc

    async def execute(self, query, params=(), fetchone=False, fetchall=False, commit=True):
        return await asyncio.to_thread(self._execute, query, params, fetchone, fetchall, commit)

    @property
    def users(self): return UsersCollection(self)
    @property
    def login_attempts(self): return LoginAttemptsCollection(self)
    @property
    def projects(self): return ProjectsCollection(self)
    @property
    def files(self): return FilesCollection(self)
    @property
    def coach_reports(self): return CoachReportsCollection(self)
    @property
    def pulse_events(self): return PulseEventsCollection(self)


# ---------- users ----------
class UsersCollection:
    def __init__(self, db): self.db = db
    async def create_index(self, *a, **k): pass

    async def find_one(self, filt, projection=None):
        clauses, params = [], []
        if "id" in filt:
            clauses.append("id = %s"); params.append(filt["id"])
        if "email" in filt:
            clauses.append("LOWER(email) = LOWER(%s)"); params.append(filt["email"])
        if not clauses:
            return None
        row = await self.db.execute(f"SELECT * FROM users WHERE {' AND '.join(clauses)} LIMIT 1",
                                    tuple(params), fetchone=True)
        if not row:
            return None
        res = dict(row)
        if projection and projection.get("password_hash") == 0:
            res.pop("password_hash", None)
        return res

    async def insert_one(self, doc):
        sql = """INSERT INTO users (id, email, name, password_hash, role, plan, created_at)
                 VALUES (%s,%s,%s,%s,%s,%s,%s)
                 ON CONFLICT (id) DO UPDATE SET email=EXCLUDED.email, name=EXCLUDED.name,
                 password_hash=EXCLUDED.password_hash, role=EXCLUDED.role, plan=EXCLUDED.plan"""
        await self.db.execute(sql, (doc["id"], doc["email"].lower(), doc.get("name", ""),
                                    doc.get("password_hash", ""), doc.get("role", "user"),
                                    doc.get("plan", "free"), doc.get("created_at")), commit=True)

    async def update_one(self, filt, update):
        sets = update.get("$set", {})
        if not sets: return
        cols, params = [], []
        for k, v in sets.items():
            cols.append(f"{k} = %s"); params.append(v)
        where = []
        if "id" in filt:
            where.append("id = %s"); params.append(filt["id"])
        if "email" in filt:
            where.append("LOWER(email) = LOWER(%s)"); params.append(filt["email"])
        if not where: return
        await self.db.execute(f"UPDATE users SET {', '.join(cols)} WHERE {' AND '.join(where)}",
                              tuple(params), commit=True)


# ---------- login_attempts ----------
class LoginAttemptsCollection:
    def __init__(self, db): self.db = db
    async def create_index(self, *a, **k): pass

    async def find_one(self, filt):
        ident = filt.get("identifier")
        if not ident: return None
        row = await self.db.execute("SELECT identifier, count, locked_until FROM login_attempts WHERE identifier = %s LIMIT 1",
                                    (ident,), fetchone=True)
        return dict(row) if row else None

    async def update_one(self, filt, update, upsert=False):
        ident = filt.get("identifier")
        if not ident: return
        sets = update.get("$set", {})
        await self.db.execute("""INSERT INTO login_attempts (identifier, count, locked_until)
                                 VALUES (%s,%s,%s)
                                 ON CONFLICT (identifier) DO UPDATE
                                 SET count=EXCLUDED.count, locked_until=EXCLUDED.locked_until""",
                              (ident, sets.get("count", 0), sets.get("locked_until") or None), commit=True)

    async def delete_one(self, filt):
        ident = filt.get("identifier")
        if ident:
            await self.db.execute("DELETE FROM login_attempts WHERE identifier = %s", (ident,), commit=True)


# ---------- projects ----------
class ProjectCursor:
    def __init__(self, db, filt):
        self.db, self.filt = db, filt
        self._sf, self._sd = "updated_at", "DESC"

    def sort(self, field, direction=-1):
        self._sf = field
        self._sd = "ASC" if direction == 1 else "DESC"
        return self

    async def to_list(self, limit=100):
        clauses, params = [], []
        if "user_id" in self.filt:
            clauses.append("user_id = %s"); params.append(self.filt["user_id"])
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(limit)
        rows = await self.db.execute(f"SELECT * FROM projects {where} ORDER BY {self._sf} {self._sd} LIMIT %s",
                                     tuple(params), fetchall=True)
        return [_clean_project(r) for r in (rows or [])]


PROJECT_COLUMNS = {
    "id", "user_id", "title", "language", "region", "idea",
    "script", "validation", "approved", "style", "scenes",
    "audio", "captions_on", "render", "step", "duration", "tone",
    "created_at", "updated_at", "brief", "content_contract", "scene_job_started_at", "scene_job_token"
}


class ProjectsCollection:
    def __init__(self, db): self.db = db
    async def create_index(self, *a, **k): pass

    async def claim_scene_job(self, pid, uid, token):
        row = await self.db.execute("""UPDATE projects SET scene_job_started_at = NOW(),
            scene_job_token = %s, updated_at = NOW()
            WHERE id = %s AND user_id = %s
              AND (scene_job_started_at IS NULL OR scene_job_started_at < NOW() - INTERVAL '25 minutes')
              AND COALESCE(render->>'status', '') <> 'rendering'
              AND NOT EXISTS (SELECT 1 FROM jsonb_array_elements(COALESCE(scenes, '[]'::jsonb)) s
                              WHERE s->>'status' IN ('queued', 'generating'))
            RETURNING scene_job_started_at""", (token, pid, uid), fetchone=True)
        return bool(row)

    async def release_scene_job(self, pid, uid, token):
        await self.db.execute("""UPDATE projects SET scene_job_started_at = NULL,
            scene_job_token = NULL, updated_at = NOW()
            WHERE id = %s AND user_id = %s AND scene_job_token = %s""", (pid, uid, token))

    async def recover_expired_scene_job(self, pid, uid, token):
        row = await self.db.execute("""UPDATE projects SET
            scenes = (SELECT COALESCE(jsonb_agg(CASE
                WHEN s->>'status' IN ('queued', 'generating')
                THEN s || '{"status":"failed","error":"Generation was interrupted. Retry missing pictures to continue."}'::jsonb
                ELSE s END ORDER BY n), '[]'::jsonb)
                FROM jsonb_array_elements(COALESCE(scenes, '[]'::jsonb)) WITH ORDINALITY AS x(s,n)),
            scene_job_started_at = NULL, scene_job_token = NULL, updated_at = NOW()
            WHERE id = %s AND user_id = %s AND scene_job_token = %s
              AND scene_job_started_at < NOW() - INTERVAL '25 minutes'
            RETURNING id""", (pid, uid, token), fetchone=True)
        return bool(row)

    async def claim_render_job(self, pid, uid, token, queued_at):
        row = await self.db.execute("""UPDATE projects SET render = %s,
            scene_job_started_at = NULL, scene_job_token = NULL, updated_at = NOW()
            WHERE id = %s AND user_id = %s
              AND COALESCE(render->>'status', '') <> 'rendering'
              AND (scene_job_started_at IS NULL OR scene_job_started_at < NOW() - INTERVAL '25 minutes')
              AND NOT EXISTS (SELECT 1 FROM jsonb_array_elements(COALESCE(scenes, '[]'::jsonb)) s
                              WHERE s->>'status' IN ('queued', 'generating'))
            RETURNING id""",
            (Json({"status": "rendering", "progress": 1, "message": "Queued",
                   "claim_token": token, "queued_at": queued_at}), pid, uid),
            fetchone=True)
        return bool(row)

    async def fail_render_claim(self, pid, uid, token):
        await self.db.execute("""UPDATE projects SET render = %s, updated_at = NOW()
            WHERE id = %s AND user_id = %s AND render->>'claim_token' = %s""",
            (Json({"status": "failed", "progress": 0,
                   "message": "Could not queue render. Please retry."}), pid, uid, token))

    async def page(self, user_id, page, size):
        totals = await self.db.execute("SELECT COUNT(*) AS total, COUNT(*) FILTER (WHERE render->>'status' = 'done') AS ready FROM projects WHERE user_id = %s", (user_id,), fetchone=True)
        rows = await self.db.execute("""SELECT id, title, language, style, step, updated_at,
            jsonb_build_object('status', render->>'status') AS render,
            COALESCE((SELECT jsonb_agg(x) FROM (SELECT jsonb_build_object('image_path', s->>'image_path') AS x
              FROM jsonb_array_elements(COALESCE(scenes::jsonb, '[]'::jsonb)) s WHERE s->>'image_path' IS NOT NULL LIMIT 1) thumbs), '[]'::jsonb) AS scenes
            FROM projects WHERE user_id = %s ORDER BY updated_at DESC, id DESC LIMIT %s OFFSET %s""",
            (user_id, size, (page - 1) * size), fetchall=True)
        return {"items": [_clean_project(r) for r in rows or []], "total": totals["total"], "ready": totals["ready"], "page": page, "size": size}

    def find(self, filt, projection=None): return ProjectCursor(self.db, filt)

    async def find_one(self, filt, projection=None):
        clauses, params = [], []
        if "id" in filt: clauses.append("id = %s"); params.append(filt["id"])
        if "user_id" in filt: clauses.append("user_id = %s"); params.append(filt["user_id"])
        if not clauses: return None
        row = await self.db.execute(f"SELECT * FROM projects WHERE {' AND '.join(clauses)} LIMIT 1",
                                    tuple(params), fetchone=True)
        return _clean_project(row)

    async def insert_one(self, doc):
        sql = """INSERT INTO projects (id, user_id, title, language, region, idea, duration, tone, script, validation,
                                       approved, style, scenes, audio, captions_on, render, step, created_at, updated_at)
                 VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                 ON CONFLICT (id) DO UPDATE SET title=EXCLUDED.title, duration=EXCLUDED.duration, tone=EXCLUDED.tone,
                 script=EXCLUDED.script, validation=EXCLUDED.validation, approved=EXCLUDED.approved, style=EXCLUDED.style,
                 scenes=EXCLUDED.scenes, audio=EXCLUDED.audio, captions_on=EXCLUDED.captions_on,
                 render=EXCLUDED.render, step=EXCLUDED.step, updated_at=EXCLUDED.updated_at"""
        await self.db.execute(sql, (
            doc["id"], doc["user_id"], doc.get("title", "Untitled story"),
            doc.get("language", "te"), doc.get("region", "Andhra Pradesh"), doc.get("idea", ""),
            doc.get("duration", 45), doc.get("tone", "Emotional"),
            Json(doc.get("script")), Json(doc.get("validation")), doc.get("approved", False),
            doc.get("style"), Json(doc.get("scenes", [])), Json(doc.get("audio")),
            doc.get("captions_on", True), Json(doc.get("render", {"status": "idle", "progress": 0})),
            doc.get("step", 1), doc.get("created_at"), doc.get("updated_at"),
        ), commit=True)

    async def update_one(self, filt, update):
        pid = filt.get("id")
        if not pid: return
        sid = filt.get("scenes.id")
        if sid:
            row = await self.db.execute("SELECT scenes FROM projects WHERE id = %s", (pid,), fetchone=True)
            if not row: return
            scenes = _parse_json(row.get("scenes")) or []
            sets, pushes = update.get("$set", {}), update.get("$push", {})
            for sc in scenes:
                if sc.get("id") == sid:
                    for k, v in sets.items(): sc[k.replace("scenes.$.", "")] = v
                    for k, v in pushes.items(): sc.setdefault(k.replace("scenes.$.", ""), []).append(v)
            scene_token = active_scene_token.get()
            guard = " AND scene_job_token = %s" if scene_token else ""
            params = (Json(scenes), pid, scene_token) if scene_token else (Json(scenes), pid)
            await self.db.execute(f"UPDATE projects SET scenes = %s, updated_at = NOW() WHERE id = %s{guard}",
                                  params, commit=True)
            return
        sets = update.get("$set", {})
        if not sets: return
        cols, params = [], []
        for k, v in sets.items():
            if k not in PROJECT_COLUMNS:
                continue
            cols.append(f"{k} = %s")
            params.append(Json(v) if k in ("script", "validation", "scenes", "audio", "render", "brief", "content_contract") and v is not None else v)
        if not cols: return
        params.append(pid)
        scene_token, render_token = active_scene_token.get(), active_render_token.get()
        guard = ""
        if scene_token:
            guard += " AND scene_job_token = %s"
            params.append(scene_token)
        if render_token:
            guard += " AND render->>'claim_token' = %s"
            params.append(render_token)
        await self.db.execute(f"UPDATE projects SET {', '.join(cols)} WHERE id = %s{guard}", tuple(params), commit=True)

    async def delete_one(self, filt):
        if filt.get("id"):
            await self.db.execute("DELETE FROM projects WHERE id = %s", (filt["id"],), commit=True)


# ---------- files ----------
class FilesCollection:
    def __init__(self, db): self.db = db
    async def create_index(self, *a, **k): pass

    async def find_one(self, filt):
        row = await self.db.execute(
            "SELECT * FROM files WHERE storage_path = %s AND user_id = %s AND is_deleted = FALSE LIMIT 1",
            (filt.get("storage_path"), filt.get("user_id")), fetchone=True)
        return dict(row) if row else None

    async def insert_one(self, doc):
        await self.db.execute(
            """INSERT INTO files (id, user_id, storage_path, content_type, size, is_deleted, created_at)
               VALUES (%s,%s,%s,%s,%s,%s,%s)""",
            (doc["id"], doc["user_id"], doc["storage_path"], doc.get("content_type", "application/octet-stream"),
             doc.get("size", 0), doc.get("is_deleted", False), doc.get("created_at")), commit=True)

    async def update_one(self, filt, update):
        path = filt.get("storage_path")
        if not path: return
        sets = update.get("$set", {})
        if "is_deleted" in sets:
            await self.db.execute("UPDATE files SET is_deleted = %s WHERE storage_path = %s",
                                  (sets["is_deleted"], path), commit=True)

    async def update_many(self, filt, update):
        paths = filt.get("storage_path", {}).get("$in", []) if isinstance(filt.get("storage_path"), dict) else []
        if not paths: return
        sets = update.get("$set", {})
        if "is_deleted" in sets:
            await self.db.execute("UPDATE files SET is_deleted = %s WHERE storage_path = ANY(%s)",
                                  (sets["is_deleted"], paths), commit=True)


# ---------- coach_reports ----------
class CoachCursor:
    def __init__(self, db, filt): self.db, self.filt = db, filt
    def sort(self, field, direction=-1): return self

    async def to_list(self, limit=20):
        rows = await self.db.execute(
            "SELECT id, user_id, input, report, created_at FROM coach_reports WHERE user_id = %s ORDER BY created_at DESC LIMIT %s",
            (self.filt.get("user_id"), limit), fetchall=True)
        return [_clean_coach(r) for r in (rows or [])]


class CoachReportsCollection:
    def __init__(self, db): self.db = db
    def find(self, filt, projection=None): return CoachCursor(self.db, filt)

    async def insert_one(self, doc):
        await self.db.execute(
            "INSERT INTO coach_reports (id, user_id, input, report, created_at) VALUES (%s,%s,%s,%s,%s)",
            (doc["id"], doc["user_id"], Json(doc.get("input")), Json(doc.get("report")), doc.get("created_at")),
            commit=True)


# ---------- pulse_events ----------
def _pulse_where(filt):
    clauses, params = [], []
    for key, val in (filt or {}).items():
        if key == "created_at" and isinstance(val, dict) and "$gte" in val:
            clauses.append("created_at >= %s"); params.append(val["$gte"])
        elif key in ("language", "region", "event", "user_id", "project_id", "genre"):
            if val:
                clauses.append(f"{key} = %s"); params.append(val)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    return where, params


class PulseEventCursor:
    def __init__(self, db, filt):
        self.db, self.filt = db, filt
        self._sf, self._sd = "created_at", "DESC"

    def sort(self, field, direction=-1):
        self._sf = field
        self._sd = "ASC" if direction == 1 else "DESC"
        return self

    async def to_list(self, limit=1000):
        where, params = _pulse_where(self.filt)
        params.append(limit)
        rows = await self.db.execute(
            f"SELECT id, user_id, event, language, region, genre, hook, idea_title, project_id, meta, created_at "
            f"FROM pulse_events {where} ORDER BY {self._sf} {self._sd} LIMIT %s",
            tuple(params), fetchall=True)
        out = []
        for r in (rows or []):
            d = dict(r)
            d["meta"] = _parse_json(d.get("meta")) or {}
            out.append(d)
        return out


class PulseEventsCollection:
    def __init__(self, db): self.db = db

    def find(self, filt, projection=None):
        return PulseEventCursor(self.db, filt)

    async def insert_one(self, doc):
        await self.db.execute(
            """INSERT INTO pulse_events (id, user_id, event, language, region, genre, hook, idea_title, project_id, meta, created_at)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (doc["id"], doc["user_id"], doc["event"], doc.get("language", ""), doc.get("region", ""),
             doc.get("genre", ""), doc.get("hook", ""), doc.get("idea_title", ""), doc.get("project_id", ""),
             Json(doc.get("meta") or {}), doc.get("created_at")),
            commit=True)

    async def count_documents(self, filt):
        where, params = _pulse_where(filt)
        row = await self.db.execute(f"SELECT COUNT(*) AS n FROM pulse_events {where}", tuple(params), fetchone=True)
        return int(row["n"]) if row else 0

    async def delete_many(self, filt):
        where, params = _pulse_where(filt)
        if where:
            await self.db.execute(f"DELETE FROM pulse_events {where}", tuple(params), commit=True)
