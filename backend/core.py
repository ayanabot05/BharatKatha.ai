import os
import uuid
import asyncio
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta

from dotenv import load_dotenv

ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env")

import bcrypt  # noqa: E402
import jwt  # noqa: E402
import mimetypes
from fastapi import Request, HTTPException  # noqa: E402

if os.environ.get("DATABASE_URL"):
    from db_supabase import SupabaseDB
    db = SupabaseDB(os.environ["DATABASE_URL"])
    client = db
else:
    from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]

JWT_SECRET = os.environ["JWT_SECRET"]
APP_NAME = "vidbharat"
CACHE = ROOT / "media_cache"
CACHE.mkdir(exist_ok=True)
log = logging.getLogger("vidbharat")


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def new_id():
    return uuid.uuid4().hex


# ---------- auth ----------
def hash_password(p: str) -> str:
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()


def verify_password(p: str, h: str) -> bool:
    return bcrypt.checkpw(p.encode(), h.encode())


def make_token(uid: str, kind: str, ttl: timedelta) -> str:
    payload = {"sub": uid, "type": kind, "exp": datetime.now(timezone.utc) + ttl}
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def cookie_options():
    secure = os.environ.get("COOKIE_SECURE", "false").lower() == "true"
    same_site = os.environ.get("COOKIE_SAMESITE", "none" if secure else "lax")
    return dict(httponly=True, secure=secure, samesite=same_site, path="/")


def set_auth_cookies(resp, uid: str):
    common = cookie_options()
    resp.set_cookie("access_token", make_token(uid, "access", timedelta(minutes=15)), max_age=900, **common)
    resp.set_cookie("refresh_token", make_token(uid, "refresh", timedelta(days=7)), max_age=604800, **common)


def decode(token: str, kinds=("access",)) -> str:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")
    if payload.get("type") not in kinds:
        raise HTTPException(401, "Invalid token type")
    return payload["sub"]


async def load_user(uid: str) -> dict:
    user = await db.users.find_one({"id": uid}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(401, "User not found")
    return user


async def current_user(request: Request) -> dict:
    token = request.cookies.get("access_token")
    auth = request.headers.get("Authorization", "")
    if not token and auth.startswith("Bearer "):
        token = auth[7:]
    if not token:
        raise HTTPException(401, "Not authenticated")
    return await load_user(decode(token))


async def media_user(request: Request) -> dict:
    # media is loaded by <img>/<video>, which can't refresh tokens — accept refresh cookie too
    for name, kinds in (("access_token", ("access",)), ("refresh_token", ("refresh",))):
        tok = request.cookies.get(name)
        if tok:
            try:
                return await load_user(decode(tok, kinds))
            except HTTPException:
                continue
    raise HTTPException(401, "Not authenticated")


# ---------- object storage ----------
STORAGE_ROOT = Path(os.environ.get("MEDIA_STORAGE_DIR") or ROOT / "storage").resolve()


def init_storage(force=False):
    STORAGE_ROOT.mkdir(parents=True, exist_ok=True)
    return str(STORAGE_ROOT)


def _storage_path(path):
    target = (STORAGE_ROOT / path).resolve()
    if not target.is_relative_to(STORAGE_ROOT) or target == STORAGE_ROOT:
        raise HTTPException(400, "Invalid media path")
    return target


def _put(path, data, ct):
    target = _storage_path(path)
    if os.environ.get("GCS_BUCKET"):
        from cloud_storage import upload
        return upload(os.environ["GCS_BUCKET"], path, data, ct)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return {"path": path}


def _get(path):
    target = _storage_path(path)
    if os.environ.get("GCS_BUCKET"):
        from cloud_storage import download
        try:
            return download(os.environ["GCS_BUCKET"], path)
        except FileNotFoundError:
            raise HTTPException(404, "Media object not found")
    if not target.is_file():
        # Preserve access to previously downloaded media after migration.
        target = CACHE / path.replace("/", "_").replace("\\", "_")
    if not target.is_file():
        raise HTTPException(404, "Media is not stored locally; regenerate or restore it")
    return target.read_bytes(), mimetypes.guess_type(path)[0] or "application/octet-stream"


async def get_object(path):
    return await asyncio.to_thread(_get, path)


async def save_media(user_id: str, kind: str, data: bytes, ext: str, ct: str) -> str:
    path = f"{APP_NAME}/{kind}/{user_id}/{new_id()}.{ext}"
    res = await asyncio.to_thread(_put, path, data, ct)
    path = res.get("path", path)
    await db.files.insert_one({"id": new_id(), "user_id": user_id, "storage_path": path, "content_type": ct,
                               "size": len(data), "is_deleted": False, "created_at": now_iso()})
    return path


async def cached(path: str) -> Path:
    local = CACHE / path.replace("/", "_")
    if not local.exists():
        data, _ = await get_object(path)
        local.write_bytes(data)
    return local
