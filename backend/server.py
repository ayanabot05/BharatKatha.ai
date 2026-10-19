import os
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from fastapi import FastAPI, APIRouter, Depends, HTTPException, Request, Response
from starlette.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from starlette.responses import JSONResponse, RedirectResponse
import beta_controls

from core import (db, client, current_user, media_user, hash_password, verify_password, set_auth_cookies, decode,
                  cookie_options, make_token, now_iso, new_id, get_object, presigned_media_url,
                  init_storage, log)
import ai
import mailer
import pulse
import youtube
import admin_auth
from admin_auth import require_admin
import auth_api
import early_access
import growth
from projects import router as projects_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
# httpx INFO logs include the full YouTube URL, including its API key.
logging.getLogger("httpx").setLevel(logging.WARNING)
app = FastAPI(title="BharatChitra AI Studio")
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
    invited = {email.strip().lower() for email in os.environ.get("BETA_INVITE_EMAILS", "").split(",") if email.strip()}
    if os.environ.get("BETA_REGISTRATION", "true").lower() != "true" and body.email.lower() not in invited:
        raise HTTPException(403, "This beta is invite-only. Contact the owner for access.")
    email = body.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(400, "Email already registered")
    user = {"id": new_id(), "email": email, "name": body.name, "password_hash": hash_password(body.password),
            "role": "user", "plan": "free", "created_at": now_iso()}
    await db.users.insert_one(dict(user))
    set_auth_cookies(response, user["id"])
    await growth.track("signup", user_id=user["id"])
    return public(user)


@api.post("/auth/login")
async def login(body: LoginIn, request: Request, response: Response):
    email = body.email.lower()
    ident = f"{request.client.host if request.client else 'x'}:{email}"
    att = await db.login_attempts.find_one({"identifier": ident})
    if att and att.get("count", 0) >= 5:
        locked = att.get("locked_until")
        locked_str = locked.isoformat() if hasattr(locked, "isoformat") else str(locked or "")
        if locked_str > now_iso():
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
async def media(path: str, download: bool = False, user=Depends(media_user)):
    rec = await db.files.find_one({"storage_path": path, "user_id": user["id"], "is_deleted": False})
    if not rec:
        raise HTTPException(404, "File not found")
    content_type = rec.get("content_type", "")
    filename = os.path.basename(path).replace('"', "") if download else ""
    if download:
        # Only an explicit download counts; inline playback must not inflate it.
        await growth.track("download", user_id=user["id"],
                           kind=content_type, path=filename)
    # Prefer a short-lived direct R2 URL: playback then costs no backend
    # bandwidth and no egress. Falls back to proxying bytes when R2 is off.
    direct = await presigned_media_url(path, filename=filename, content_type=content_type)
    if direct:
        return RedirectResponse(direct, status_code=307,
                                headers={"Cache-Control": "private, max-age=300"})
    data, ct = await get_object(path)
    headers = {"Cache-Control": "private, max-age=86400"}
    if download:
        headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    return Response(content=data, media_type=content_type or ct, headers=headers)


# ---------- meta / ideas / voice ----------
@api.get("/meta")
async def meta():
    import piper_tts
    import supertonic_tts
    import premium_tts
    try:
        piper_languages = sorted(piper_tts.voices())
    except RuntimeError as exc:
        log.warning("Piper configuration is unavailable: %s", exc)
        piper_languages = []
    try:
        premium_rates = premium_tts.pricing()
    except RuntimeError as exc:
        log.warning("Premium voice pricing is unavailable: %s", exc)
        premium_rates = {}
    configured_voice_provider = os.environ.get("TTS_PROVIDER", "edge").lower()
    default_voice_provider = configured_voice_provider
    if default_voice_provider in {"google_chirp", "openai"} and default_voice_provider not in premium_rates:
        default_voice_provider = "edge"
    voice_engine = {
        "google_chirp": "Google Cloud Chirp 3 HD",
        "openai": "OpenAI TTS",
        "piper": "Operator-hosted Piper voice",
        "supertonic": "Cloud-hosted Supertonic 3 voice" if os.environ.get("SUPERTONIC_HINDI_SERVICE_URL") else "Local Supertonic 3 voice",
        "edge": "Two Edge neural voices per language",
    }.get(default_voice_provider, "Unavailable voice provider")
    return {"voices": ai.VOICES, "languages": ai.LANGS, "styles": list(ai.STYLE_PROMPTS.keys()),
            "premium_voice_rates": premium_rates,
            "voice_providers": [
                {"id": "piper", "name": "Piper (open source)", "type": "open", "languages": piper_languages},
                {"id": "supertonic", "name": "Supertonic 3", "type": "open",
                 "languages": ["hi", "en"] if supertonic_tts.available() else []},
                {"id": "edge", "name": "Edge neural voice", "type": "hosted", "languages": [] if os.environ.get("APP_ENV") == "production" else sorted(ai.EDGE_VOICES)},
                {"id": "google_chirp", "name": "Google Chirp 3 HD (premium)", "type": "premium", "languages": sorted(ai.CHIRP_LANGUAGES) if configured_voice_provider == "google_chirp" and "google_chirp" in premium_rates else []},
                {"id": "openai", "name": "OpenAI TTS (premium)", "type": "premium", "languages": sorted(ai.EDGE_VOICES) if configured_voice_provider == "openai" and "openai" in premium_rates and os.environ.get("OPENAI_API_KEY") else []},
            ], "default_voice_provider": default_voice_provider,
            "engines": {"script": "Gemini text API", "images": "Vertex AI image worker" if ai.IMAGE_PROVIDER == "worker" else "Gemini image API",
                        "voice": voice_engine, "captions": "Script timing or Whisper"},
            "ram_ai": {"version": "2.0", "kind": "rule-guided prompt layer",
                       "note": "Stable prompt release. Feedback is collected for human review; no automatic training."},
            # "email" -> reset links are emailed; "manual" -> written to the server
            # log for the operator to relay. The UI tells the user which is true.
            "password_reset_delivery": mailer.delivery_mode(),
            "video_motion": {"full_ai_available": False,
                             "note": "Full AI video motion is not live yet; the studio animates stills with real camera motion."}}


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
    provider: Optional[str] = None
    max_cost_inr: Optional[float] = Field(default=None, gt=0)


@api.post("/voice/preview")
async def voice_preview(body: PreviewIn, user=Depends(current_user)):
    import premium_tts
    try:
        premium_tts.authorize((body.provider or os.environ.get("TTS_PROVIDER", "edge")).lower(),
                              [body.text], body.max_cost_inr)
    except RuntimeError as exc:
        raise HTTPException(400, str(exc)) from exc
    try:
        data = await ai.tts(body.text, body.voice, body.speed, body.language,
                            provider=body.provider or "", max_cost_inr=body.max_cost_inr)
    except Exception as e:
        raise HTTPException(502, f"Voice preview failed: {e}")
    return Response(content=data, media_type="audio/mpeg")


# ---------- pulse ----------
@api.get("/pulse/weekly")
async def pulse_weekly(language: str = "", region: str = "", admin=Depends(require_admin)):
    return await pulse.weekly_pulse(language, region)


@api.get("/pulse/report")
async def pulse_report(admin=Depends(require_admin)):
    # Operator view: the whole deployment, not one account. An administrator is
    # no longer a user, so there is no user id to scope this to.
    return await pulse.learning_report()


@api.get("/pulse/winners")
async def pulse_winners(language: str = "te", region: str = "", limit: int = 6, user=Depends(current_user)):
    return {"hooks": await pulse.pulse_hooks_for(language, region, limit, user_id=user["id"])}


# ---------- growth coach ----------
class VideoStat(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    views: Optional[int] = Field(default=None, ge=0)
    avg_viewed_pct: Optional[float] = Field(default=None, ge=0, le=1000)
    viewed_vs_swiped_pct: Optional[float] = Field(default=None, ge=0, le=100)
    likes: Optional[int] = Field(default=None, ge=0)
    retention: List[Optional[float]] = Field(default_factory=list, max_length=7)


class CoachIn(BaseModel):
    channel_name: str = Field(default="My channel", max_length=200)
    niche: str = Field(default="Stories", max_length=200)
    language: str = Field(default="te", max_length=10)
    subscribers: Optional[int] = Field(default=None, ge=0)
    videos: List[VideoStat] = Field(min_length=1, max_length=10)
    goal: Optional[str] = Field(default=None, max_length=500)


@api.post("/coach/analyze")
async def coach_analyze(body: CoachIn, user=Depends(current_user)):
    if any(value is not None and (not 0 <= value <= 1000) for video in body.videos for value in video.retention):
        raise HTTPException(422, "Retention must be a positive percentage or left blank.")
    try:
        report = await ai.coach(body.model_dump())
    except Exception as e:
        raise HTTPException(502, f"Analysis failed: {e}")
    doc = {"id": new_id(), "user_id": user["id"], "input": body.model_dump(), "report": report, "created_at": now_iso()}
    await db.coach_reports.insert_one(dict(doc))
    return doc


class FeedbackIn(BaseModel):
    project_id: Optional[str] = Field(default=None, max_length=64)
    rating: int = Field(ge=1, le=5)
    area: str = Field(min_length=1, max_length=40)
    comment: str = Field(min_length=3, max_length=2000)
    permission_to_train: bool = False


@api.post("/feedback")
async def feedback(body: FeedbackIn, user=Depends(current_user)):
    project = None
    if body.project_id:
        project = await db.projects.find_one({"id": body.project_id, "user_id": user["id"]})
        if not project:
            raise HTTPException(404, "Project not found")
    record = {"id": new_id(), "user_id": user["id"], "event": "beta_feedback",
              "language": (project or {}).get("language", ""), "region": "", "genre": "", "hook": "",
              "idea_title": "", "project_id": body.project_id or "", "created_at": now_iso(),
              "meta": {**body.model_dump(exclude={"project_id"}), "reviewed": False, "release": "phase-0",
                       "project_updated_at": (project or {}).get("updated_at")}}
    # Unlike optional activity logging, feedback must persist before showing success.
    await db.pulse_events.insert_one(record)
    return {"id": record["id"], "saved": True}


@api.get("/feedback")
async def feedback_inbox(admin=Depends(require_admin)):
    return await db.pulse_events.find({"event": "beta_feedback"}, {"_id": 0}).sort("created_at", -1).to_list(50)


@api.get("/coach/reports")
async def coach_reports(user=Depends(current_user)):
    return await db.coach_reports.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(20)


@api.get("/health")
@api.get("/")
async def root():
    return {"app": "BharatChitra AI Studio", "ok": True}


@api.get("/ready")
async def ready():
    """Check database and persistent storage without exposing configuration."""
    try:
        if os.environ.get("DATABASE_URL"):
            await db.execute("SELECT 1", fetchall=True)
        else:
            await db.command("ping")
        import r2_storage
        r2_on = r2_storage.configured()
        bucket_name = os.environ.get("GCS_BUCKET")
        if os.environ.get("APP_ENV") == "production" and not (r2_on or bucket_name):
            raise RuntimeError("Persistent storage is unconfigured")
        if r2_on:
            # HeadBucket proves the bucket exists and the token can read it.
            if not await asyncio.to_thread(
                    lambda: r2_storage.client().head_bucket(Bucket=r2_storage.bucket())):
                raise RuntimeError("Persistent storage is unavailable")
        elif bucket_name:
            from cloud_storage import client
            if not await asyncio.to_thread(lambda: client().bucket(bucket_name).exists(timeout=10)):
                raise RuntimeError("Persistent storage is unavailable")
    except Exception:
        log.error("Readiness check failed: database or storage unavailable")
        raise HTTPException(503, "Service dependencies are unavailable")
    return {"ok": True}


app.include_router(api)
app.include_router(projects_router)

import billing_api  # noqa: E402 - routers are attached after app construction
app.include_router(billing_api.router)
app.include_router(billing_api.admin_router)
app.include_router(admin_auth.router)
app.include_router(auth_api.router)
app.include_router(early_access.router)
app.include_router(early_access.admin_router)
app.include_router(growth.router)
app.include_router(growth.admin_router)

cors_origins = [] if os.environ.get("APP_ENV") == "production" else [
    "http://localhost:3004", "http://127.0.0.1:3004",
]
env_frontend = os.environ.get("FRONTEND_URL", "").strip()
if env_frontend:
    for u in env_frontend.split(","):
        u_clean = u.strip()
        if u_clean and u_clean not in cors_origins:
            cors_origins.append(u_clean)

app.add_middleware(CORSMiddleware, allow_credentials=True, allow_origins=cors_origins,
                   allow_methods=["*"], allow_headers=["*"])


@app.middleware("http")
async def beta_boundary(request: Request, call_next):
    path = request.url.path
    production = os.environ.get("APP_ENV") == "production"
    if path.startswith("/api/") and request.method in {"POST", "PATCH", "DELETE", "PUT"}:
        origin = request.headers.get("origin")
        if origin and origin not in cors_origins:
            return JSONResponse({"detail": "This website is not allowed to change your studio."}, status_code=403)
        if production or os.environ.get("RATE_LIMIT_ENABLED") == "true":
            try:
                ident = beta_controls.identity(request)
                allowed, wait = await beta_controls.consume(ident + ":writes", 30, 60)
                if allowed and path not in {"/api/auth/refresh", "/api/auth/logout"}:
                    allowed, wait = await beta_controls.consume(ident + ":daily", 200, 86400)
                if not allowed:
                    return JSONResponse({"detail": f"Beta limit reached. Please try again in {wait} seconds."},
                                        status_code=429, headers={"Retry-After": str(wait)})
            except Exception:
                log.exception("Beta rate limiter unavailable")
                return JSONResponse({"detail": "The studio is temporarily busy. Please try again shortly."}, status_code=503)
    response = await call_next(request)
    if path.startswith("/api/") and not path.startswith("/api/media/"):
        response.headers["Cache-Control"] = "private, no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@app.on_event("startup")
async def startup():
    if os.environ.get("APP_ENV") == "production":
        if not os.environ.get("DATABASE_URL"):
            raise RuntimeError("Phase 0 production requires Supabase DATABASE_URL")
        await db.execute("SELECT brief, content_contract FROM projects LIMIT 0", fetchall=True)
        await db.execute("SELECT scene_job_started_at, scene_job_token FROM projects LIMIT 0", fetchall=True)
        await db.execute("SELECT bucket FROM request_limits LIMIT 0", fetchall=True)
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
    # The administrator is a separate credential store, never a users row.
    seeded = await admin_auth.ensure_admin(os.environ["ADMIN_EMAIL"],
                                           os.environ["ADMIN_PASSWORD"])
    if not seeded:
        log.error("Administrator credentials were NOT stored. Run migrations/004_auth_growth_notify.sql "
                  "against DATABASE_URL; admin sign-in stays closed until then.")
    try:
        init_storage()
    except Exception as e:
        log.error(f"Storage init failed: {e}")
        if os.environ.get("APP_ENV") == "production":
            raise RuntimeError("Cloud storage is unavailable; fix storage access before accepting users") from e


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
