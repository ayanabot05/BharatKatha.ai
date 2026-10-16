# Verified implementation state

**16 October launch pivot:** Founder says Hindi and Telugu quality was good. Treat this as founder listening acceptance of those local samples, while retaining the separate license, caption, cloud and public-flow gates. The new target is a conditional commercial-ready beta by 18 October. Launch languages are Telugu and Hindi, plus English only after a real end-to-end check; all others are Coming Soon. Main backend deployment is the first priority. The deployed image worker is a different service. No main backend URL or public smoke test has been verified yet.

Updated: 16 October 2026. Source: repository inspection, cited test reports and checks in `TEST_RESULTS.md`.

**Latest Hindi execution:** A pinned, local CPU Supertonic 3 M1 model produced three real Hindi MP3s at 1.789–2.858 s inference time and 499.2 MiB peak process RSS. The isolated Hindi Studio preview, narration save, estimated-caption warnings, five-image FFmpeg render, browser playback and MP4 download all passed. The MP4 audio matches saved narration at 0.999942 correlation and displays an AI-generated narration label. Founder listening feedback was favorable; detailed fluent-speaker and human caption synchronization review remain open. The Telugu baseline was not modified. Nine languages still lack real open-model samples. See [the Hindi report](../test_reports/SUPERTONIC_HINDI_REAL_2026-10-16.md).

**Latest Telugu execution:** The local Studio backend generated a live 58,558-byte Piper preview, saved 23.64 seconds of `te_IN-padmavathi-medium` narration, and rendered a new 23.61-second MP4 from the five existing approved images. The 17.563-second render has 11 estimated SRT captions. Full FFmpeg decode passed; decoded MP4 audio correlates 0.99999 with the newly saved Piper narration. Studio browser audio/video playback, both estimated-caption warnings and the MP4 download passed; the downloaded hash matches the export. Fluent Telugu review and human caption synchronization remain. See [the live evidence](TEST_RESULTS.md).

| Area | State | Gap |
| --- | --- | --- |
| Accounts/projects | Implemented routes, ownership checks, Supabase adapter | Public two-account isolation test pending |
| Scripts/RAM AI | Gemini calls, creator edits, rule-guided review | Slow/quota-limited; no open text route or verified consolidated planner |
| Scenes/images | Gemini/worker path, regeneration, approval and continuity gates | No open image provider or fresh visual benchmark |
| Narration | Edge default; configured Chirp and OpenAI require explicit request selection and typed cost budget; upload/recording | Telugu Piper and Hindi local Supertonic 3 have real three-case MP3s and local Studio MP4 exports. All 11 have the same corpus and evidence reporter; nine still need real open-model inference. Detailed fluent-speaker quality and premium actual billing reconciliation are pending |
| Captions | Edge word boundaries, Chirp cloud STT, fallback estimates | Piper currently has estimated timing; saved audio now labels that status and Studio shows a review notice. Local alignment and measured synchronization remain unimplemented |
| Export | 720 × 1280 still-image FFmpeg render, MP4/SRT/thumbnail | No AI motion, music wiring, exact duration or 1080p preset |
| Growth Coach | Manual stats and Gemini report, saved history | No YouTube URL/channel analysis; no private analytics |
| Deployment | Image worker previously deployed | Main API and public route not deployed; durable jobs missing |

All pre-existing uncommitted changes were preserved. See `git status` before modifying related files. The reported 40–60 minute flow and 5–10 minute target are founder estimates, not measured baselines for a fixed workload.

Local `C:` free space was about 2.59 GB at the initial checkpoint. A single roughly 64 MB Telugu Piper model was subsequently downloaded for a bounded CPU evaluation; this does not establish capacity for larger models. Cloud authentication was restored and the [live read-only audit](CLOUD_READ_ONLY_AUDIT_2026-10-15.md) now records billing, service and quota state.

## P0 execution state — 15 October 2026

The Telugu live API, project render and browser journey now pass. Fluent-speaker listening and human caption synchronization are still needed before language quality acceptance. The [controlled Windows runbook](P0_TELUGU_CLOUD_RUNBOOK.md) gives the local commands. The Audio Studio and Render pages warn that Piper caption timing is estimated; regeneration does not create measured word timestamps.

Cloud SDK authentication is restored for `ayana-video-studio`. Project billing is enabled and its account is open in INR. One CPU-only Cloud Run image worker exists. Compute Engine's project-wide GPU quota is zero despite an `asia-south1` regional L4 quota of one. Vertex AI reports an L4 serving quota of one; Cloud Run L4 effective quota was not returned. Free-trial status, remaining credits and actual GPU provisioning eligibility remain unverified. The in-app Billing Overview requested a fresh Google password, which was not entered. No cloud resource or billing mutation was made; see the [cloud audit](CLOUD_READ_ONLY_AUDIT_2026-10-15.md).

Indic Parler's publisher lists all 11 app languages, gated access, Apache-2.0 model weights and 0.9B F32 parameters. Account acceptance and authenticated weight access are not confirmed. The training-data table's `CC V1` entry requires rights clarification; no measured host requirement, project GPU quota or inference run exists. A public ONNX export cannot resolve those gates. The [language matrix](AUDIO_LANGUAGE_COVERAGE.md) remains the acceptance ledger; Telugu, Hindi, Tamil and Marathi are the primary group, and the other seven remain tracked.

**Latest local Studio attempt:** Piper and FastAPI started outside the sandbox with Piper explicitly selected and premium rates empty. Local login and project listing both returned HTTP 200. The list included an approved five-scene Telugu project with five real ready approved images. The next unsandboxed inspection was rejected by automatic approval review after the host reached its usage limit; it did not execute. No Studio preview/save/render/download result followed. The first blocked dependency is approval review, not an application endpoint. See [TEST_RESULTS](TEST_RESULTS.md).
