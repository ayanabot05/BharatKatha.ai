# Task tracker

## Launch pivot — 16 October 2026

| ID | Status | Launch gate |
| --- | --- | --- |
| LAUNCH-API | Active | Audit production config, cost and cloud resources; deploy main FastAPI API to Cloud Run; verify HTTPS health, login, project ownership and persistence. Current repository has no verified deployed main API URL. |
| LAUNCH-VOICES | Active | Founder accepted local Hindi and Telugu sound quality. Preserve those pipelines and verify English end to end. Package Linux-accessible Hindi weights and Telugu Piper service; no local Windows path dependency in cloud. |
| LAUNCH-VIDEO | Pending API | Real cloud five-image narration/caption render, persistent media, public playback/SRT/MP4 download, failure and multi-user checks. |
| LAUNCH-LEGAL | Pending | Exact model/runtime rights and attribution, AI narration disclosure, privacy/terms, support, asset rights and paid-plan gate. |
| LAUNCH-RELEASE | Pending | Public launch only after all critical functionality, security, licensing and billing gates pass; otherwise private beta or delay. |

The remaining nine-language audio work and later script/image/motion expansion are paused until after launch. Older audio-first next-action text below is historical.

Updated: 16 October 2026. Do not mark a task complete without evidence in `TEST_RESULTS.md`.

| ID | Status | Task and checkpoint |
| --- | --- | --- |
| AUDIT-001 | Complete for repository audit | Reconciled all three directives with code, reports, deployment and Growth Coach in the master plan and current state. Live cloud billing/resource inspection is separately tracked as CLOUD-001. |
| AUDIO-001 | Complete for local integration | Explicit Piper route, preview/generation selection, license/revision gate, fail-closed behavior and benchmark harness. Backend/frontend regressions pass and three real Telugu samples were generated through the adapter. Deployed app end-to-end check remains a separate gate. |
| AUDIO-002 | Active | The same three-case corpus and evidence reporter cover all 11 app languages. The [execution checkpoint](../test_reports/AUDIO_11_LANGUAGE_EXECUTION_2026-10-15.md) now shows real Telugu and Hindi samples and Studio exports; the remaining nine have no real open-model samples. Tamil and Marathi are next in the primary group, with all seven secondary languages following the same evidence gates. Detailed fluent-speaker and human caption-synchronization review remain. |
| AUDIO-003 | Active | Telugu padmavathi model card cites CC BY 4.0 IndicVoices-R dataset; local CPU inference works. Record attribution/GPL distribution obligations before production. Indic Parler gated/3.75 GB; no local HF token, no verified cloud quota/billing and only 6.08 GiB RAM available at checkpoint. Public ONNX export evaluated but not runnable here. IndicF5 MIT/gated/1.4 GB plus reference-voice consent; Indic-Speak hosting permission requirement. Piper Hindi pratham has a noncommercial dataset; Hindi rohan and several English voices inherit lessac, whose dataset license is research-only; Telugu maya terms unresolved. |
| ROUTER-001 | Active | Audio premium preflight now requires an operator all-in rate, hard request cap, typed creator budget and no automatic paid retries. Unified cross-capability model router, actual-cost ledger and benchmark selection remain. |
| SCRIPT-001 | Pending | Open instruct-model path and reduced duplicate analysis after audio feasibility report. |
| IMAGE-001 | Pending | Open-weight image benchmark/integration after audio gate. |
| VIDEO-001 | Pending | Open motion benchmark/integration after audio gate. |
| JOBS-001 | Pending | Durable scene jobs, restart recovery and cancellation. |
| COACH-001 | Pending | Preserve current Coach regression; implement URL/channel imports later without invented analytics. |
| CLOUD-001 | Active | Cloud CLI auth restored; live read-only billing, Cloud Run, Vertex AI, Compute quota, API and storage inventory completed. Trial credit/account type remains unverified; GPU provisioning remains blocked. See [cloud audit](CLOUD_READ_ONLY_AUDIT_2026-10-15.md). No cloud mutation or spend authorized. |
| BUG-001 | Active environment limitation | Async pytest and the real local Piper preview request still stall inside sandbox; prior focused suite and the earlier real Piper adapter probe passed outside it. The new pure caption-status test passed, but the updated async Piper cache test and preview attempt were interrupted in the sandbox. |
| BUG-002 | Blocked external demo | AI4Bharat's public Indic Parler Space returned `Error: No API found` for a Hindi short-script attempt. No sample resulted. Continue self-hosted/access and ONNX feasibility work under AUDIO-003; do not infer a model defect from the demo error. |

## P0 blocker resolution checkpoint — 15 October 2026

| ID | Status | Task and checkpoint |
| --- | --- | --- |
| AUDIO-004 | Complete for controlled Telugu app flow; quality review pending under AUDIO-002 | Live preview MP3, persisted Piper narration, five-image Studio render, estimated SRT/warnings, new MP4 full decode, audio identity, browser audio/video playback and browser download passed. The first render call failed HTTP 400 because an older valid review fingerprint omitted `brief`; compatibility was repaired without changing the story or calling a paid reviewer. Fluent listening and human synchronization review remain under AUDIO-002. See [TEST_RESULTS](TEST_RESULTS.md). |
| AUDIO-005 | Complete for controlled local Hindi flow; quality review pending under AUDIO-002 | Commercially conditional OpenRAIL-M Supertonic 3 M1 selected after rejecting noncommercial Piper Hindi cards. Three real CPU MP3s, 14 focused backend tests, frontend build, browser preview/save, estimated captions, five-image MP4 with AI narration disclosure, browser playback/download and audio identity passed. Founder listening feedback was favorable; fluent per-case rubric, human caption sync, hosted deployment and model training-data provenance remain. See [Hindi evidence](../test_reports/SUPERTONIC_HINDI_REAL_2026-10-16.md). |
| CLOUD-001 | BLOCKED for GPU use | Reauthentication succeeded. Billing is enabled, regional Compute L4 quota is 1 but project-wide GPU quota is 0, Vertex L4 serving quota is 1, and Cloud Run L4 quota has no returned effective limit. Trial status and actual provisioning eligibility remain unverified. See [cloud audit](CLOUD_READ_ONLY_AUDIT_2026-10-15.md). |
| AUDIO-003 | BLOCKED | Indic Parler model card confirms gate and Apache-2.0 weights, but account acceptance and authenticated file access are unverified. Training-data `CC V1` rights, measured RAM/VRAM and project GPU quota remain open. Keep all 11 languages on the existing coverage matrix; no ONNX shortcut assumed. |

Next action: execute the same commercially reviewed real-sample and Studio gates for Tamil, Marathi and the seven secondary languages, while collecting detailed Hindi/Telugu listening and caption synchronization review. Preserve Growth Coach and existing creator flows; do not start unrelated development.
