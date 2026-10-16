# BharatKatha product and engineering plan

## Launch directive — 16 October 2026 (supersedes the sequence below)

Target a working commercial-ready beta by **18 October 2026**, conditional on critical functionality, security, licensing and billing checks. Freeze launch languages to Telugu (Piper), Hindi (Supertonic 3), and English after a real end-to-end check. Show the other eight languages as Coming Soon. The founder accepted the observed Hindi and Telugu audio quality; that feedback does not itself complete model rights, caption synchronization or cloud checks. Preserve Growth Coach and all existing project/editing flows.

Execute in this order: (1) audit and deploy the **main FastAPI API** to `ayana-video-studio` in `asia-south1`, then connect the Vercel frontend; (2) complete a real cloud render with persistent media and three verified voices; (3) close commercial/security gates; (4) launch only if every critical gate passes. Stop Tamil/Marathi and other language experiments, open-model scripts/images, true motion, rewrites and cosmetic work until after launch. Do not overwrite the separate `vidbharat-image-worker`.

Before a billable deployment, check current credits, quotas and alerts, estimate cost, and obtain founder approval for meaningful new charges. No GPU or paid plan is part of this beta. A deployment is not launch proof: registration/login, account isolation, persistence, real video, playback and download must pass on public URLs. If a critical gate fails, limit access to a private beta or postpone.

Updated: 15 October 2026. Status terms: **Verified** means checked in code or an existing test report; **Tested** means a test was run in this session; **Proposed** means implementation remains; **Blocked** means an external prerequisite is missing.

## Product objective

Build a general creator studio for scripts, scenes, narration, captions, video, and Growth Coach. Optimize for speed while preserving story and visual quality, creator editing, account isolation, and completed assets. Fast, Balanced, and Cinematic modes are proposed; there are no measured cost or time estimates to show creators yet.

## Verified current architecture

- React frontend with account, library, studio and Growth Coach pages. FastAPI backend with authentication, project ownership, Supabase persistence, private media routes, Google Cloud Storage integration, Gemini text and image routes, Edge/Chirp/OpenAI speech routes, and FFmpeg export.
- Actual export is 720 × 1280 H.264/AAC from approved still scenes with camera movement. True generated video, lip sync, 1080p presets, and direct social publishing are unimplemented.
- Growth Coach accepts creator-entered channel/video numbers and produces a Gemini-based report. YouTube Data API supports idea discovery. Coach URL and channel import, transcript analysis, and private analytics authorization are unimplemented.
- Script and image calls use Gemini. The image worker has been deployed before, but the main backend has not. Work runs inside a single API process; durable queue and restart recovery are unimplemented.
- Existing `test_reports/EDIT_JOURNEY_2026-10-15.md` records 215 simulated workflow tests and seven in-process real database/API checks. `test_reports/FRESH_CLOUD_VIDEO_2026-10-15.md` records no fresh cloud video and no public multi-user test.

## Code audit against the October 15 directives

| Directive | Code evidence | Gap/status |
| --- | --- | --- |
| Preserve account and editing workflow | `backend/server.py`, `backend/projects.py`, `frontend/src/pages/Studio.jsx` | **Verified in code**; public journey pending |
| Preserve Growth Coach and YouTube integration | `backend/server.py` Coach routes, `backend/youtube.py`, `frontend/src/pages/Coach.jsx` | **Verified in code**; URL/channel import and transcript analysis **proposed** |
| Open-source Indian narration first | Edge/Chirp/OpenAI in `backend/ai.py`; Piper adapter in `backend/piper_tts.py`; three real Telugu CPU samples; equal smoke corpus and evidence tracker for all 11 app languages | **Partial**; Telugu, Hindi, Tamil and Marathi must reach the same real-sample and review gate first; all other languages follow the same stages |
| Avoid unnecessary paid transcription | Edge supplies word boundaries; Chirp invokes cloud STT in `backend/projects.py` | Local forced alignment **proposed**; Piper uses estimates |
| Open-source script path and unified router | Gemini selection and fallback loop in `backend/ai.py`; rules in `backend/ram_ai.py`; premium audio cost gate in `backend/premium_tts.py` | Open text route, benchmark-based selection and cross-capability provider metadata **proposed**; audio premium rate verification pending |
| Open images with quality preservation | Gemini image routes and worker in `backend/ai.py`, `deploy/image-worker/` | Open image output/quality benchmark **proposed after audio** |
| True AI motion | FFmpeg still render in `backend/render.py` | Real motion provider **proposed after audio** |
| Durable jobs and measured costs | In-process task tracking in `backend/projects.py`; `backend/beta_controls.py` limits | Restart recovery, provider cost ledger, benchmark baseline **proposed** |
| Commercial deployment | `deploy/` configurations; existing image worker evidence | Main API, public routing, billing verification, two-account test **blocked/pending** |

**Performance suspects, not measured conclusions:** script/review invoke multiple Gemini calls; scene pictures are generated sequentially; Chirp caption timing can add a separate cloud recognition call; rendering depends on an in-process job. Instrument stage boundaries and run a fixed workload before changing concurrency or claiming a speed gain.

**Existing risks:** image/story mismatch in past real outputs, duration drift, scene approvals invalidated by edits, provider quota exhaustion, and job loss after backend restart. Regression gates must cover these before broadening launch.

## Refined implementation sequence

| Phase | Work | Acceptance evidence |
| --- | --- | --- |
| 0. Preserve and baseline | Verify feature inventory, Growth Coach, active edits, quota behavior, cloud inventory, per-stage timings | Regression results; inventory and measured timings |
| 1. Open-source audio | License and hardware review; run real TTS for all 11 creation languages, with Telugu/Hindi/Tamil/Marathi as the first complete cohort; compare explicit Chirp where approved; preserve audio reuse and avoid unnecessary paid STT | Each language has saved real samples, runtime/model version, latency, listening review and no unintended paid calls; primary cohort receives deeper quality review |
| 2. Scripts and RAM AI | Open instruct-model adapter and benchmark; consolidate planning; deterministic checks and cache | Real script approved without Gemini; quality, latency, cost evidence |
| 3. Images | Benchmark eligible open weights against current Gemini images; implement standard route only if quality threshold passes | Real scene image, scene editing, visual review, no unapproved Gemini call |
| 4. Video and render | Optimize FFmpeg, music and duration; test open image-to-video provider | Playable verified motion clip, intact fast render mode |
| 5. Production | Durable jobs, backend deployment, public routing, account isolation and recovery | Public two-account end-to-end and restart test, billing measurements |
| 6. Commercial | Pricing, limits and margins based on actual completed workflows | Measured cost and acceptance rates |

Growth Coach regression, security, project persistence, and README updates apply in every phase. No phase is complete merely because code compiles or a provider can be configured.

## Candidate decisions and constraints

- **Audio:** The [language coverage audit](AUDIO_LANGUAGE_COVERAGE.md) tracks all 11 offered languages with Telugu, Hindi, Tamil and Marathi as the first acceptance cohort. Indic Parler-TTS is Apache 2.0 per its [model card](https://huggingface.co/ai4bharat/indic-parler-tts) and lists all 11, but its roughly 3.75 GB weight file exceeds the initial laptop free space before dependencies; access is gated. [IndicF5](https://huggingface.co/ai4bharat/IndicF5) is MIT and covers nine app languages, excluding Urdu and English. Its 1.4 GB weight file is gated; it requires reference audio/transcript and permission for voice cloning. [Indic-Speak](https://huggingface.co/bodhan-ai/indic-speak) labels all 11 as production tier but requires permission for hosting for others, so it is blocked as a default hosted choice. Piper code is [GPLv3](https://github.com/OHF-Voice/piper1-gpl/blob/main/COPYING); its [voice catalog](https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/VOICES.md) does not list Tamil or Marathi. The [Telugu padmavathi voice](https://huggingface.co/rhasspy/piper-voices/commit/ff43c1e79f98a765202dcfb03710851f9ec4ff2e) cites CC BY 4.0 IndicVoices-R and generated three real CPU samples; attribution/distribution review and native-speaker listening are pending. Piper is a low-resource candidate, not a full language solution or quality winner. [faster-whisper](https://github.com/SYSTRAN/faster-whisper/blob/master/LICENSE) is a proposed local transcription candidate under MIT.
- **Images and video:** FLUX.1 schnell, SDXL, Wan 2.2 and Wan2GP are evaluation candidates only. No open-weight image or moving-video output has been verified in this repository.
- **Cloud:** Use `ayana-video-studio` if feasible. Existing records say GPU VM creation was rejected under free-trial billing. Current credit, quota, hardware, storage and real cloud cost are unverified. Do not create paid resources or download large weights to the laptop without approval.
- **Architecture:** Audio preview and narration now require explicit premium selection, operator all-in rate, hard INR cap and creator budget. Evolve this into a provider-neutral model router with benchmark ranking, actual-cost records and deterministic fallback rules. Add durable per-scene jobs after the audio baseline. Preserve approved scenes and assets on retry.

## Target architecture and cost rules

```text
Creator request → durable project job → scene tasks → provider router
                                      ├─ validated open model (default when available)
                                      └─ premium model (explicit selection + budget)
             → versioned private assets → quality/review gates → FFmpeg export
             → stage timings, model version, actual/estimated cost, job status
```

The router must consider task, language, quality mode, hardware, availability, license, benchmark, latency and budget. A selected provider failure returns an actionable error and retains completed assets. Switching to premium requires an explicit choice and a bounded budget; a service-level environment choice alone is insufficient for commercial launch.

**Cost status:** no trustworthy per-video amount can be calculated from the current records. The local Telugu CPU probe used no new paid cloud or premium API calls; electricity was not metered. Open weights can still incur VM/Cloud Run compute, storage, downloads and egress. The incremental cash ceiling is ₹2,000 and is **not** spending authorization. Before any cloud run, record the exact command, machine, runtime limit, projected maximum cost and cleanup steps, then obtain approval.

**Fallback plan:** retain the working Edge/Chirp options while open audio is evaluated; return an unavailable message when a selected open route lacks a model, rather than switching silently. Retain Gemini scene generation until an open image passes the same prompt and visual review. Retain FFmpeg still-image export while true motion is evaluated. Do not weaken approvals, ownership or render gates to improve apparent speed.

## File-level plan

- Audio: `backend/piper_tts.py`, `backend/benchmark_piper_audio.py`, `backend/ai.py`, `backend/projects.py`, `backend/server.py`, `frontend/src/studio/StepAudio.jsx`, `backend/tests/test_piper_tts.py`.
- Scripts: `backend/ai.py`, `backend/ram_ai.py`, `backend/projects.py`, new provider and evaluation modules.
- Images: `backend/ai.py`, `backend/projects.py`, `deploy/image-worker/`, scene UI and tests.
- Video/jobs: `backend/render.py`, `backend/projects.py`, new job/worker modules, deployment config and tests.
- Coach: `backend/server.py`, `backend/youtube.py`, `frontend/src/pages/Coach.jsx`; preserve existing report route and API key handling.

The founder's October 15 directives supersede older `plan/plan.md` descriptions of 1080p AI clips and paid providers as an MVP. That older plan is historical, not a statement of shipped features.
