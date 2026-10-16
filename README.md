# BharatKatha — creator studio

An evolving AI creation studio for ideas, reviewed scripts, editable scenes,
narration, captions, downloadable video and Growth Coach. The currently tested
release is a private beta; the broader open-source-first product directive is
tracked in [the master plan](docs/PROJECT_MASTER_PLAN.md).

## Status — 16 October 2026

| Capability | Current evidence |
| --- | --- |
| Accounts, project editing and private media | Implemented locally; public two-account journey pending |
| Scripts and scene images | Gemini routes and a previously deployed image worker; open-model routes pending |
| Narration | Edge legacy default; explicit, budget-gated Chirp/OpenAI alternatives; Telugu Piper and Hindi local Supertonic routes. All 11 creation languages have three-case scripts. Telugu and Hindi have real open-model samples and local Studio MP4 exports; the other nine have no real samples yet |
| Video | 720 × 1280 FFmpeg still-image animation; no generated motion or lip sync |
| Growth Coach | Manual video statistics and AI report; YouTube Data API discovery is separate; URL/channel analysis pending |
| Production | Main API and durable job queue not deployed |

The 11-language audio phase remains **partial**. Telugu and Hindi have verified local
pipelines; fluent-speaker rubrics, human caption synchronization and nine languages
remain open. See [current state](docs/CURRENT_STATE.md), [task tracker](docs/TASK_TRACKER.md),
[audio feasibility](docs/AUDIO_FEASIBILITY_2026-10-15.md),
[test evidence](docs/TEST_RESULTS.md), [11-language audio coverage](docs/AUDIO_LANGUAGE_COVERAGE.md),
the [execution checkpoint](test_reports/AUDIO_11_LANGUAGE_EXECUTION_2026-10-15.md),
the [fluent-speaker review form](docs/AUDIO_NATIVE_REVIEW_TEMPLATE.md),
and [session handoff](docs/SESSION_HANDOFF.md).
Prior full regression evidence is 238 backend tests plus six subtests. The latest
11-language corpus and premium-gate focus passed 11 backend tests; an earlier
Piper-focused run passed 11. The updated frontend suite passed 14 tests. A separate
real Telugu Piper and Hindi Supertonic probes establish local inference and
decodable output. The founder reported the Hindi samples sounded good; a
case-by-case fluent-speaker rubric is still pending.
The reported 40–60 minute generation time and 5–10 minute target are not yet a
controlled benchmark. No new paid cloud resources or premium inference were used.
The latest caption-status change passed a focused backend check and a frontend
production build; an expanded async backend run stalled in the sandbox and was
interrupted. The public Indic Parler demo also returned `Error: No API found`
for a Hindi sample request, so it provided no new audio evidence.

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
          |-- Gemini: current scripts and images
          |-- Speech: Edge / Chirp / OpenAI; Piper HTTP or local Supertonic 3
          |-- FFmpeg: final video assembly on the cloud machine
```

The frontend calls API endpoints only. Database credentials and provider keys
stay on the backend. Supabase is the supported Phase 0 production database.
Large models, datasets, training and rendering belong in cloud infrastructure.
The production architecture keeps model weights out of the API process. For the
bounded local feasibility probe, one roughly 64 MB Telugu voice was downloaded
to the ignored `backend/.piper-models/` directory.

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
| `backend/piper_tts.py` | Adapter for a separately hosted Piper HTTP voice service |
| `backend/supertonic_tts.py` | Pinned local CPU Hindi voice; no automatic model download or paid fallback |
| `backend/audio_eval_corpus.py`, `audio_coverage.py` | Equal speech probe cases and evidence stages for all 11 creation languages |
| `backend/ram_ai.py` | Language and story structure checks |
| `backend/db_supabase.py` | Server-side PostgreSQL adapter and paginated library query |
| `backend/beta_controls.py` | Atomic request counters for private-beta limits |
| `backend/pulse.py` | Activity records; no automatic training |
| `backend/render.py`, `cloud_storage.py` | Video assembly and private cloud media |
| `backend/migrations/` | Additive database migrations; run with `migrate.py` |
| `backend/tests/`, `frontend/src/studio/*.test.jsx` | Regression tests |
| `deploy/` | Cloud and Vercel deployment instructions/configuration |
| `test_reports/` | Evaluation evidence; not runtime application code |
| `docs/` | Current plan, task tracker, decisions, tests and session handoff |

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

Frontend: http://localhost:3004. API: http://localhost:8000.
The migration extends an existing database schema; it is not a fresh-database bootstrap.
Use the existing Supabase project or restore its schema before running migrations.

### Open-source audio route

**P0 status (16 October 2026):** The controlled Telugu Studio flow now passes through browser download. The preview API generated a 58,558-byte Piper MP3 in 5.245 seconds. The project saved 23.64 seconds of `te_IN-padmavathi-medium` narration in 17.226 seconds, then rendered a new 23.61-second captioned MP4 from its five existing approved images in 17.563 seconds between render events. FFmpeg decoded the full export; its audio matches the newly saved Piper narration. Studio browser audio/video playback, both estimated-caption warnings and the MP4 download passed; the downloaded hash matches the export. Fluent Telugu review and human caption synchronization remain before quality acceptance. Exact paths, timings and the resolved legacy review-fingerprint failure are in [TEST_RESULTS](docs/TEST_RESULTS.md). Use the [controlled local runbook](docs/P0_TELUGU_CLOUD_RUNBOOK.md) to reproduce. All 11 languages remain in the [coverage matrix](docs/AUDIO_LANGUAGE_COVERAGE.md).

Cloud CLI authentication is restored. The [authenticated read-only cloud audit](docs/CLOUD_READ_ONLY_AUDIT_2026-10-15.md) records billing, current infrastructure and GPU quota limits. Trial credit and actual GPU provisioning eligibility remain unverified; no cloud resources or billing settings were changed.

**Hindi Phase 2 (16 October 2026):** The three real local Supertonic 3 M1 MP3s passed decode and signal checks, with 1.789–2.858 s CPU inference and 499.2 MiB peak process RSS. A separate Hindi five-image Studio fixture passed browser preview, saved narration, estimated captions, FFmpeg MP4, browser playback and attachment download. The 23.3 s MP4 audio correlates 0.999942 with the saved local narration and carries a visible AI-narration label. The [Hindi evidence report](test_reports/SUPERTONIC_HINDI_REAL_2026-10-16.md) has sample paths and exact results. The founder said the Hindi sounded good; detailed fluent-speaker scoring and human caption synchronization are still open.

Piper was checked first: its published Hindi voice cards or the `lessac` lineage raise noncommercial dataset restrictions. The selected [Supertonic 3 model](https://huggingface.co/supertone-oss-archive/supertonic-3) bundles the evaluated M1 voice under [OpenRAIL-M terms](https://huggingface.co/supertone-oss-archive/supertonic-3/blob/main/LICENSE), which permit commercial deployment subject to use restrictions and clear AI-generated-content disclosure. Its Python code is MIT; the weights retain their own license. For an operator-controlled Hindi setup, install `backend/requirements-open-tts.txt`, download only the pinned archived ONNX assets and M1 voice style plus LICENSE, then set `SUPERTONIC_HINDI_MODEL_DIR` and the revision shown in `backend/.env.example`. The API never downloads weights or falls back to a paid voice. The 398,667,957-byte local model is ignored by Git. Its training-data provenance is not detailed in the public model card, so production rights review remains open.

The optional Piper adapter expects an operator-hosted
[Piper HTTP server](https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/API_HTTP.md)
with a commercially cleared voice for each enabled language. Configure
`PIPER_VOICES_JSON` in the backend environment. Each language entry needs
`url`, `model_id`, `model_revision`, `license_url`,
`license_status="verified-commercial"`, and `hardware_requirements`.
The service must return WAV from
`POST /synthesize`; the backend converts it to MP3 for existing storage and
rendering. The creator selects Piper in Audio Studio for preview and generation.
If no verified voice entry exists for a language, Piper is unavailable and the
request fails clearly. A failed selected provider is never replaced by a paid
provider. Saved scene audio records the model revision and synthesis latency;
changing the configured model invalidates that scene's audio cache.

Run `python backend/audio_coverage.py` from the repository root to see the current
evidence for every creation language. The same short, names/numbers and dialogue
smoke scripts are in `backend/audio_eval_corpus.py` for all 11 languages. With a
licensed Piper voice service for a specific language, run the bounded real-sample
probe from `backend`:

```powershell
python benchmark_piper_audio.py --language te --output ../test_reports/piper-audio-te-YYYY-MM-DD
```

Change `--language` to any configured app language. The command writes three MP3 samples and a JSON
report for that language. Piper's published voice catalog does not cover Tamil or
Marathi, so a broader multilingual candidate is required for the four-language
priority group. The report leaves actual and estimated
infrastructure cost unset until billing evidence exists; native speakers must
review pronunciation and quality. The probe never calls a paid speech API.

The adapter itself downloads no voice weights. Premium speech routes must also be
enabled by the backend operator before a creator can select them. Piper's
maintained code is GPLv3 and
individual voice weights can have different licenses; check the exact voice
model card before marking an entry commercially verified. A configured endpoint is not proof
of audio quality, timing or cost. The real Telugu probe is documented in
[`test_reports/PIPER_TELUGU_REAL_2026-10-15.md`](test_reports/PIPER_TELUGU_REAL_2026-10-15.md).
The [execution checkpoint](test_reports/AUDIO_11_LANGUAGE_EXECUTION_2026-10-15.md)
lists sample paths, measured times, app pipeline status and blockers for all 11 languages.
Generated Piper
audio currently has estimated caption timing, which the saved audio status and
Studio notice identify; local alignment remains work.
Premium speech also requires an explicit provider value in each request; the
backend environment setting alone cannot trigger a paid call.

The operator must set `TTS_PREMIUM_MAX_REQUEST_INR` and
`TTS_PREMIUM_RATES_JSON` with a current, conservative all-in INR rate per 1,000
characters and model ID. Chirp entries must set `includes_caption_stt: true`
because generated captions can invoke separate cloud transcription. Example
structure (illustrative rate only; verify the current rate before use):

```json
{"google_chirp":{"model_id":"chirp3-hd","all_in_inr_per_1000_chars":"2.00","includes_caption_stt":true}}
```

The creator sees an estimate and types a maximum INR budget before preview or
full narration. The API checks the budget and operator cap before a premium
call. Premium generation and caption timing are not automatically retried
because a failed attempt may already be billed. Saved project audio records
the estimate and leaves actual cost unset until billing evidence is available.

## Content and editing rules

- Category, audience, platform, language, region, tone and approximate duration
  travel with the story. Length is a guide; required actions and an earned ending
  take priority over a rigid scene or word count.
- The creator’s brief is persisted and included in the review fingerprint.
- Script/narration changes clear stale approval, audio and final renders. A changed
  scene must get a matching picture again; unchanged scenes can retain theirs.
- Pictures are generated sequentially and checked against the story. Failed
  images remain unapproved. Do not bypass those gates for a higher score.
- Edge provides word boundaries; Chirp uses separate cloud speech recognition
  for measured timing; Piper currently uses estimated timing.
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
python -m pytest tests/test_phase_zero.py tests/test_material_review.py tests/test_review_fixes.py tests/test_output_integrity.py tests/test_language_quality.py tests/test_local_setup.py tests/test_beta.py tests/test_piper_tts.py tests/test_premium_tts.py tests/test_audio_coverage.py -q
cd ../frontend
npm run build
node node_modules/@craco/craco/dist/bin/craco.js test --watchAll=false --runInBand
```

Before inviting friends, verify login and account isolation on the deployed URL,
then generate one real story through download, submit feedback, and restart the
backend. `/api/health` reports process health only, not provider/database readiness.

## Known limits

Private, supervised beta only. No direct social publishing or paid subscriptions.
Growth Coach currently accepts manually entered statistics and does not import
YouTube video URLs, channels or private analytics. Premium speech now has
request-level estimate and budget gates; production pricing still needs current
rates, billing reconciliation and end-to-end checks. Three Telugu Piper and three
Hindi Supertonic samples decoded successfully; Telugu fluent-speaker review and
Hindi case-by-case quality review remain open. Open-model samples for nine
languages are outstanding. The 100% completion target for Telugu, Hindi,
Tamil and Marathi and 90% for the other seven are requested work priorities,
not measured quality scores; no language is accepted until its audio and fluent-speaker
review are recorded. Indic Parler weights remain gated; no GPU resource or cloud
spending was started. The bounded 398.7 MB local Hindi model download and CPU
evaluation are recorded in the Hindi evidence report.
Some interface explanations still fall back to English; full native-language UI
review is not complete. Jobs are in-process and need one continuously running
backend. Public scale, durable jobs and GPU model fine-tuning are future work.
