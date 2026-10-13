# VidBharat Studio

React frontend: http://localhost:3003. FastAPI backend: http://localhost:8000.
Port 3000 is left available for your other application.

## Run locally (PowerShell, two terminals)

Frontend:
```powershell
cd C:\Users\gunak\Downloads\VidBharat\frontend
npm ci
npm start
```

Backend (existing Python installation):
```powershell
cd C:\Users\gunak\Downloads\VidBharat\backend
python -m pip install -r requirements.txt
python -m uvicorn server:app --host 127.0.0.1 --port 8000 --reload
```

For a fresh installation, create and activate a Python virtual environment first.
Copy each `.env.example` to `.env` only if `.env` does not already exist. Preserve
existing database credentials. `DATABASE_URL` selects Supabase PostgreSQL;
otherwise `MONGO_URL` and `DB_NAME` select MongoDB. Existing PostgreSQL tables
must already be provisioned; the adapter does not create the database schema.

Set `GEMINI_API_KEY` for scripts/images and `OPENAI_API_KEY` for voice/transcription
in `backend/.env`. Model names can be overridden using the example variables.
The application can start without AI keys; generation reports a configuration error
until they are supplied. Provider usage is billed to those provider accounts.

Media is saved under `backend/storage` (override with `MEDIA_STORAGE_DIR`). Back up
this directory along with the database. Previously cached media remains readable;
old remotely stored media that was never downloaded must be restored or regenerated.

Use `http://localhost:3003` consistently for the frontend. Development cookies use
SameSite=Lax and HTTP. Set `COOKIE_SECURE=true` for HTTPS deployment and set
`FRONTEND_URL` to the actual allowed frontend origin. Never expose backend `.env`.

## Verification

```powershell
cd frontend
npm run build
cd ../backend
python -m unittest discover -s tests -p test_local_setup.py
```

`GET /api/health` is a process health endpoint, not a database/provider readiness check.
A 401 on `/api/auth/me` before sign-in is expected.

## Styling fix

The CRACO PostCSS extension converted the plugin array into a callback. With the
installed PostCSS loader this left Tailwind directives unprocessed. CRA already
loads Tailwind from `tailwind.config.js`; the redundant override has been removed.
After configuration changes, stop the frontend with Ctrl+C, restart `npm start`,
and refresh the browser. A successful webpack compilation alone does not prove
Tailwind generated its utility CSS.

Use npm and the committed package-lock.json consistently. The old CRA toolchain
still produces Node deprecation notices; these do not cause the missing styles.
Dependency audit findings require a separate compatibility review; do not run
`npm audit fix --force` blindly.
