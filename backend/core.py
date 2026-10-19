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
APP_NAME = os.environ.get("APP_STORAGE_PREFIX") or "bharatchitra"
CACHE = ROOT / "media_cache"
CACHE.mkdir(exist_ok=True)
log = logging.getLogger("bharatchitra")


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def new_id():
    return uuid.uuid4().hex


def is_operator(user) -> bool:
    """True for operator accounts, which bypass the beta daily limits.

    This replaces the old ``role == 'admin'`` bypass. Administrators no longer
    have a row in ``users`` at all, so the exemption is now an explicit,
    operator-configured email list (``OPERATOR_EMAILS``, plus ``ADMIN_EMAIL``).
    """
    email = ((user or {}).get("email") or "").strip().lower()
    if not email:
        return False
    allowed = {e.strip().lower() for e in os.environ.get("OPERATOR_EMAILS", "").split(",") if e.strip()}
    admin_email = (os.environ.get("ADMIN_EMAIL") or "").strip().lower()
    if admin_email:
        allowed.add(admin_email)
    return email in allowed


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


def remote_backend():
    """Which remote object store serves media: "r2", "gcs" or "" for local disk.

    R2 wins when configured because its egress is free and video playback is
    almost entirely egress. Set R2_BUCKET to switch over; unset it to fall back
    without a code change.
    """
    import r2_storage
    if r2_storage.configured():
        return "r2"
    if os.environ.get("GCS_BUCKET"):
        return "gcs"
    return ""


def _put(path, data, ct):
    target = _storage_path(path)
    backend = remote_backend()
    if backend == "r2":
        import r2_storage
        return r2_storage.upload(path, data, ct)
    if backend == "gcs":
        from cloud_storage import upload
        return upload(os.environ["GCS_BUCKET"], path, data, ct)
    if os.environ.get("APP_ENV") == "production":
        raise RuntimeError("Production media storage is not configured: Cloudflare R2 credentials required.")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return {"path": path}


def _get(path):
    target = _storage_path(path)
    backend = remote_backend()
    if backend == "r2":
        import r2_storage
        try:
            return r2_storage.download(path)
        except FileNotFoundError:
            raise HTTPException(404, "Media object not found")
    if backend == "gcs":
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


def _delete(path):
    backend = remote_backend()
    if backend == "r2":
        import r2_storage
        r2_storage.delete(path)
        return
    if backend == "gcs":
        from cloud_storage import client
        client().bucket(os.environ["GCS_BUCKET"]).blob(path).delete()
        return
    target = _storage_path(path)
    if target.is_file():
        target.unlink()


async def delete_object(path: str) -> bool:
    """Best-effort media delete. A missing object is never an error.

    Media soft-deleted in Postgres but left in the bucket keeps costing
    storage, so callers that mark is_deleted should drop the object too.
    """
    try:
        await asyncio.to_thread(_delete, path)
        return True
    except Exception as exc:  # noqa: BLE001 - deletion must not break a request
        log.warning("Media delete failed for %s: %s", path, exc)
        return False


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


async def presigned_media_url(path: str, expires_in: int = 3600, filename: str = "",
                              content_type: str = "") -> str:
    """Direct R2 URL so video and image playback skips this API entirely.

    Egress is the expensive part of serving media and R2 charges nothing for
    it. Returns "" when R2 is not the active backend so the caller can fall
    back to proxying the bytes.
    """
    if remote_backend() != "r2":
        return ""
    import r2_storage
    try:
        return await asyncio.to_thread(
            r2_storage.presigned_url, path, expires_in, filename, content_type)
    except Exception as exc:  # noqa: BLE001 - a failed presign falls back to proxy
        log.warning("Presign failed for %s: %s", path, exc)
        return ""

