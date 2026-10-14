import os
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from fastapi import FastAPI, APIRouter, Depends, HTTPException, Request, Response
from starlette.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field

from core import (db, client, current_user, media_user, hash_password, verify_password, set_auth_cookies, decode,
                  cookie_options, make_token, now_iso, new_id, get_object, init_storage, log)
import ai
import pulse
import youtube
from projects import router as projects_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
# httpx INFO logs include the full YouTube URL, including its API key.
logging.getLogger("httpx").setLevel(logging.WARNING)
app = FastAPI(title="VidBharat Studio")
api = APIRouter(prefix="/api")


# ---------- auth ----------
class RegisterIn(BaseModel):
    name: str = Field(min_length=1)
    email: EmailStr
    password: str = Field(min_length=6)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


def public(u):
    return {k: u[k] for k in ("id", "email", "name", "role", "plan", "created_at") if k in u}


@api.post("/auth/register")
async def register(body: RegisterIn, response: Response):
    if os.environ.get("BETA_REGISTRATION", "true").lower() != "true":
        raise HTTPException(403, "This beta is invite-only. Contact the owner for access.")
    email = body.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(400, "Email already registered")
    user = {"id": new_id(), "email": email, "name": body.name, "password_hash": hash_password(body.password),
            "role": "user", "plan": "free", "created_at": now_iso()}
    await db.users.insert_one(dict(user))
    set_auth_cookies(response, user["id"])
    return public(user)


@api.post("/auth/login")
async def login(body: LoginIn, request: Request, response: Response):
    email = body.email.lower()
    ident = f"{request.client.host if request.client else 'x'}:{email}"
    att = await db.login_attempts.find_one({"identifier": ident})
    if att and att.get("count", 0) >= 5 and att.get("locked_until", "") > now_iso():
        raise HTTPException(429, "Too many attempts. Try again in 15 minutes.")
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(body.password, user["password_hash"]):
        count = (att or {}).get("count", 0) + 1
        lock = (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat() if count >= 5 else ""
        await db.login_attempts.update_one({"identifier": ident}, {"$set": {"count": count, "locked_until": lock}}, upsert=True)
        raise HTTPException(401, "Invalid email or password")
    await db.login_attempts.delete_one({"identifier": ident})
    set_auth_cookies(response, user["id"])
    return public(user)


@api.post("/auth/logout")
async def logout(response: Response):
    for k in ("access_token", "refresh_token"):
        response.delete_cookie(k, **cookie_options())
    return {"ok": True}


@api.post("/auth/refresh")
async def refresh(request: Request, response: Response):
    tok = request.cookies.get("refresh_token")
    if not tok:
        raise HTTPException(401, "No refresh token")
    uid = decode(tok, ("refresh",))
    response.set_cookie("access_token", make_token(uid, "access", timedelta(minutes=15)), max_age=900,
                        **cookie_options())
    return {"ok": True}


@api.get("/auth/me")
async def me(user=Depends(current_user)):
    return public(user)


# ---------- media ----------
@api.get("/media/{path:path}")
async def media(path: str, user=Depends(media_user)):
    rec = await db.files.find_one({"storage_path": path, "user_id": user["id"], "is_deleted": False})
    if not rec:
        raise HTTPException(404, "File not found")
    data, ct = await get_object(path)
    return Response(content=data, media_type=rec.get("content_type", ct), headers={"Cache-Control": "private, max-age=86400"})


# ---------- meta / ideas / voice ----------
@api.get("/meta")
async def meta():
    voice_engine = ("Google Cloud Chirp 3 HD" if os.environ.get("TTS_PROVIDER", "edge").lower() == "google_chirp"
                    else "Two Edge neural voices per language by default; optional OpenAI TTS when explicitly configured")
    return {"voices": ai.VOICES, "languages": ai.LANGS, "styles": list(ai.STYLE_PROMPTS.keys()),
            "engines": {"script": "Gemini text API", "images": "Vertex AI image worker" if ai.IMAGE_PROVIDER == "worker" else "Gemini image API",
                        "voice": voice_engine, "captions": "Script timing or Whisper"},
            "ram_ai": {"version": "2.0", "kind": "rule-guided prompt layer",
                       "note": "Not a trained model. Feedback loop learns from your own users."}}


class IdeasIn(BaseModel):
    language: str = "te"
    region: str = "Andhra Pradesh"
    category: str = "Moral stories"
    platform: str = "YouTube Shorts"
    audience: str = "Families & kids"


@api.post("/ideas/suggest")
async def ideas(body: IdeasIn, user=Depends(current_user)):
    try:
        data = await ai.suggest_ideas(body.language, body.region, body.category, body.platform, body.audience, user["id"])
    except Exception as e:
        raise HTTPException(502, f"Idea generation failed: {e}")
    for idea in data:
        await pulse.log_event(user["id"], "idea_shown", body.language, body.region,
                              genre=body.category, hook=idea.get("hook", ""), idea_title=idea.get("title_en", ""))
    return {"ideas": data}


@api.get("/ideas/trending")
async def trending(language: str = "te", region: str = "Andhra Pradesh",
                   category: str = "Moral stories", audience: str = "Families & kids",
                   user=Depends(current_user)):
    try:
        result = await youtube.relevant_india(language, region, category, audience)
    except Exception as e:
        raise HTTPException(503, str(e))
    return {"source": "YouTube Data API recent video search", "region": "IN", **result}


@api.post("/ideas/pick")
async def ideas_pick(body: dict, user=Depends(current_user)):
    """Frontend calls this when the user picks one idea from the list."""
    await pulse.log_event(user["id"], "idea_picked", body.get("language", ""), body.get("region", ""),
                          genre=body.get("genre", ""), hook=body.get("hook", ""), idea_title=body.get("title", ""))
    return {"ok": True}


class PreviewIn(BaseModel):
    voice: str = "fable"
    text: str = Field(min_length=1, max_length=300)
    speed: float = 1.0
    language: str = ""


@api.post("/voice/preview")
async def voice_preview(body: PreviewIn, user=Depends(current_user)):
    try:
        data = await ai.tts(body.text, body.voice, body.speed, body.language)
    except Exception as e:
        raise HTTPException(502, f"Voice preview failed: {e}")
    return Response(content=data, media_type="audio/mpeg")


# ---------- pulse ----------
@api.get("/pulse/weekly")
async def pulse_weekly(language: str = "", region: str = "", user=Depends(current_user)):
    if user.get("role") != "admin":
        raise HTTPException(403, "Admin access required")
    return await pulse.weekly_pulse(language, region)


@api.get("/pulse/report")
async def pulse_report(user=Depends(current_user)):
    if user.get("role") != "admin":
        raise HTTPException(403, "Admin access required")
    return await pulse.learning_report(user["id"])


@api.get("/pulse/winners")
async def pulse_winners(language: str = "te", region: str = "", limit: int = 6, user=Depends(current_user)):
    return {"hooks": await pulse.pulse_hooks_for(language, region, limit, user_id=user["id"])}


# ---------- growth coach ----------
class VideoStat(BaseModel):
    title: str
    views: int = 0
    avg_viewed_pct: float = 0
    viewed_vs_swiped_pct: float = 0
    likes: int = 0
    retention: List[float] = []


class CoachIn(BaseModel):
    channel_name: str = "My channel"
    niche: str = "Stories"
    language: str = "te"
    subscribers: int = 0
    videos: List[VideoStat] = Field(min_length=1)
    goal: Optional[str] = None


@api.post("/coach/analyze")
async def coach_analyze(body: CoachIn, user=Depends(current_user)):
    try:
        report = await ai.coach(body.model_dump())
    except Exception as e:
        raise HTTPException(502, f"Analysis failed: {e}")
    doc = {"id": new_id(), "user_id": user["id"], "input": body.model_dump(), "report": report, "created_at": now_iso()}
    await db.coach_reports.insert_one(dict(doc))
    return doc


@api.get("/coach/reports")
async def coach_reports(user=Depends(current_user)):
    return await db.coach_reports.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(20)


@api.get("/health")
@api.get("/")
async def root():
    return {"app": "VidBharat Studio", "ok": True}


app.include_router(api)
app.include_router(projects_router)

cors_origins = [
    "http://localhost:3003",
    "http://127.0.0.1:3003",
]
env_frontend = os.environ.get("FRONTEND_URL", "").strip()
if env_frontend:
    for u in env_frontend.split(","):
        u_clean = u.strip()
        if u_clean and u_clean not in cors_origins:
            cors_origins.append(u_clean)

app.add_middleware(CORSMiddleware, allow_credentials=True, allow_origins=cors_origins,
                   allow_methods=["*"], allow_headers=["*"])


@app.on_event("startup")
async def startup():
    if os.environ.get("APP_ENV") == "production":
        if not os.environ.get("GCS_BUCKET"):
            raise RuntimeError("Cloud beta requires GCS_BUCKET for persistent media")
        if os.environ.get("ALLOW_IMAGE_FALLBACK", "false").lower() == "true":
            raise RuntimeError("Cloud beta cannot use placeholder image fallback")
        if os.environ.get("COOKIE_SECURE", "false").lower() != "true":
            raise RuntimeError("Cloud beta requires secure cookies and HTTPS")
    await db.users.create_index("email", unique=True)
    await db.users.create_index("id", unique=True)
    await db.projects.create_index([("user_id", 1), ("updated_at", -1)])
    await db.files.create_index("storage_path")
    await db.login_attempts.create_index("identifier")
    email, pw = os.environ["ADMIN_EMAIL"].lower(), os.environ["ADMIN_PASSWORD"]
    admin = await db.users.find_one({"email": email})
    if not admin:
        await db.users.insert_one({"id": new_id(), "email": email, "name": "Admin",
                                   "password_hash": hash_password(pw), "role": "admin",
                                   "plan": "studio", "created_at": now_iso()})
    elif not verify_password(pw, admin["password_hash"]):
        await db.users.update_one({"email": email}, {"$set": {"password_hash": hash_password(pw)}})
    try:
        init_storage()
    except Exception as e:
        log.error(f"Storage init failed: {e}")


@app.on_event("shutdown")
async def shutdown():
    if hasattr(client, "close"):
        client.close()


# The cloud image serves frontend and API on one origin. Local development keeps CRA.
from pathlib import Path
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

frontend_dist = Path(os.environ.get("FRONTEND_DIST", "../frontend/build")).resolve()
if os.environ.get("SERVE_FRONTEND", "false").lower() == "true" and frontend_dist.is_dir():
    app.mount("/static", StaticFiles(directory=frontend_dist / "static"), name="static")

    @app.get("/{path:path}", include_in_schema=False)
    async def frontend(path: str):
        if path == "api" or path.startswith("api/"):
            raise HTTPException(404, "API route not found")
        candidate = (frontend_dist / path).resolve()
        if not candidate.is_relative_to(frontend_dist):
            raise HTTPException(404, "File not found")
        return FileResponse(candidate if candidate.is_file() else frontend_dist / "index.html")
