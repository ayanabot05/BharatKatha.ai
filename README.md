# BharatKatha / VidBharat — Phase 0

A private beta for turning a creator’s idea into a reviewed story, scene pictures,
natural narration, captions and a downloadable vertical video.

## Current release

The frontend is prepared for Vercel. The existing Cloud Run image worker is live;
the main API/render backend still needs a cloud deployment. Do not point the
frontend at the image worker: it does not provide login, projects or rendering.
See [Phase 0 deployment](deploy/PHASE_ZERO.md) for the release steps and gates.
No automatic model training takes place. Native-speaker review remains necessary;
a small automated test set does not establish 95% accuracy for all user topics.

## Architecture

```text
Browser / Vercel React frontend
          | HTTPS /api (Vercel proxy)
Google Cloud FastAPI backend, one process
          |-- Supabase PostgreSQL: accounts, projects, reviews, feedback
          |-- Private Google Cloud Storage: pictures, voices, finished videos
          |-- Managed AI services: scripts, image generation, speech
          |-- FFmpeg: final video assembly on the cloud machine
```

The frontend calls API endpoints only. Database credentials and provider keys
stay on the backend. Supabase is the supported Phase 0 production database.
Large models, datasets, training and rendering belong in cloud infrastructure.
There is no need to download model weights onto the laptop.

## Code map

| Folder/file | Responsibility |
| --- | --- |
| `frontend/src/pages/` | Landing, library dashboard, studio, coach, account settings |
| `frontend/src/studio/` | Idea, script, style, scenes, voice and export steps |
| `frontend/src/components/` | Navigation, reusable controls, preview, feedback form |
| `frontend/src/context/` | Signed-in account and display-language state |
| `frontend/src/lib/api.js` | API client, session refresh, safe user-facing errors |
| `backend/server.py` | HTTP app, authentication, coach, feedback, origin checks |
| `backend/projects.py` | Project workflow, approval and asset invalidation |
| `backend/ai.py` | Provider calls and evidence-based content/image review |
| `backend/ram_ai.py` | Language and story structure checks |
| `backend/db_supabase.py` | Server-side PostgreSQL adapter and paginated library query |
| `backend/beta_controls.py` | Atomic request counters for private-beta limits |
| `backend/pulse.py` | Activity records; no automatic training |
| `backend/render.py`, `cloud_storage.py` | Video assembly and private cloud media |
| `backend/migrations/` | Additive database migrations; run with `migrate.py` |
| `backend/tests/`, `frontend/src/studio/*.test.jsx` | Regression tests |
| `deploy/` | Cloud and Vercel deployment instructions/configuration |
| `test_reports/` | Evaluation evidence; not runtime application code |

## Local development

Run commands from this repository. Preserve existing `.env` files; do not overwrite
credentials. Copy `.env.example` only for a new setup.

```powershell
cd frontend
npm ci
npm start
```

```powershell
cd backend
python -m pip install -r requirements-cloud.txt
python migrate.py
python -m uvicorn server:app --host 127.0.0.1 --port 8000
```

Frontend: http://localhost:3003. API: http://localhost:8000.
The migration extends an existing database schema; it is not a fresh-database bootstrap.
Use the existing Supabase project or restore its schema before running migrations.

## Content and editing rules

- Category, audience, platform, language, region, tone and approximate duration
  travel with the story. Length is a guide; required actions and an earned ending
  take priority over a rigid scene or word count.
- The creator’s brief is persisted and included in the review fingerprint.
- Script/narration changes clear stale approval, audio and final renders. A changed
  scene must get a matching picture again; unchanged scenes can retain theirs.
- Pictures are generated sequentially and checked against the story. Failed
  images remain unapproved. Do not bypass those gates for a higher score.
- Managed voices use natural pauses. Caption timing uses measured speech timing.
- Feedback is stored as `beta_feedback` in `pulse_events`, with release and project
  revision metadata, `reviewed=false`, and training permission off by default.
  Admins can read the newest 50 entries at `GET /api/feedback`.
- `PERSONALIZED_HOOKS=false` keeps the prompt stable during this beta. Training
  requires a separate, explicitly reviewed and permissioned dataset/evaluation.

## Performance and operations

Routes load on demand. The library fetches 12 summaries per page and one thumbnail
per story. Hashed frontend assets are cached; account API responses are not shared
or publicly cached. Studio polling is sequential and slows in hidden tabs.

Supabase indexes support owner/date listing, media ownership lookup and event
queries. PostgreSQL request counters enforce write limits atomically. Redis is
not required for this small beta; adding a second cache service before a measured
need would add operational cost. A durable task queue is still required before
multiple API workers or autoscaling.

Clean expired request counters regularly on the cloud database:

```sql
DELETE FROM request_limits WHERE expires_at < now();
```

Media files live in private GCS in production. Render working folders are temporary.
Do not remove local media caches while renders are running. Do not commit `.env`,
credentials, model weights, generated videos, or training data.

## Verification

```powershell
cd backend
python -m pytest tests/test_phase_zero.py tests/test_material_review.py tests/test_review_fixes.py tests/test_output_integrity.py tests/test_language_quality.py tests/test_local_setup.py tests/test_beta.py -q
cd ../frontend
npm run build
node node_modules/@craco/craco/dist/bin/craco.js test --watchAll=false --runInBand
```

Before inviting friends, verify login and account isolation on the deployed URL,
then generate one real story through download, submit feedback, and restart the
backend. `/api/health` reports process health only, not provider/database readiness.

## Known limits

Private, supervised beta only. No direct social publishing or paid subscriptions.
Some interface explanations still fall back to English; full native-language UI
review is not complete. Jobs are in-process and need one continuously running
backend. Public scale, durable jobs and GPU model fine-tuning are future work.
