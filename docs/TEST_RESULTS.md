# Test and evidence log

## 16 October launch pivot

Founder feedback: Hindi and Telugu audio quality was good. This is a listening acceptance of the local results in the Hindi and Telugu reports, not a public deployment or license clearance. English has no verified cloud end-to-end result yet. The new main-API Cloud Run deployment and its public health/login/project smoke tests have not been run; do not report a backend URL until one is returned and tested.

## 16 October 2026 — real Hindi Supertonic 3 and Studio

The [Hindi execution report](../test_reports/SUPERTONIC_HINDI_REAL_2026-10-16.md) records the exact model/voice license, three real MP3 paths, cold/warm CPU/RAM measurements, local five-image Studio fixture and exported MP4. The official Piper Hindi voice options were rejected on individual dataset or source-voice commercial restrictions. Supertonic 3 M1 at revision `aafc6e32416a594460b32413efc49d7fe4ce6d46` was downloaded to an ignored local folder; no GPU or paid speech call occurred.

| Stage | Status | Actual evidence |
| --- | --- | --- |
| Three Hindi MP3s | PASS | 39,939 / 98,120 / 47,446 bytes; 3.413 / 7.523 / 3.971 s duration; 2.814 / 2.858 / 1.789 s CPU inference wall time. All decoded with finite non-silent samples. |
| Hardware | PASS | Cold model load 2.503 s; peak process RSS 499.2 MiB on an eight-logical-CPU machine with four ONNX intra-op threads. No GPU. |
| Browser preview and save | PASS | Isolated API `8001` and frontend `3004`; preview and narration-save POSTs HTTP 200. Project `43ae08193d8e4659aece55d6f3fa2001` persisted `provider=supertonic`, five pinned M1 model IDs and a 373,698-byte, 23.33 s MP3. Browser audio player entered play state. |
| Captions | PASS for estimated timing | Studio Audio and Render warnings visible, 16 SRT entries and burned Hindi captions. Human synchronization NOT TESTED. |
| MP4 and browser | PASS | 3,171,862-byte, 23.3 s [export](../test_reports/supertonic-hindi-2026-10-16/hindi_studio_final.mp4) fully decoded by FFmpeg. Browser video `readyState=4`, `paused=false`, no error. A frame shows the AI narration disclosure. Browser download completed; attachment header only on `?download=1`. |
| Audio identity | PASS | Decoded MP4 audio versus saved Supertonic narration correlation 0.999942. |
| Human quality | BLOCKED | Founder said “hindi was good”; per-case fluent-speaker rubric, word audit and human caption sync were not supplied. |
| Regression | PASS | Focused backend provider suite: 14 passed. Frontend production build passed. First sandbox async run stalled and was interrupted; the controlled unsandboxed run passed. |

The fixture reused five previously approved real Telugu visual assets with separate Hindi narration and a test-only approval fingerprint. It did not modify the Telugu project or invoke paid script/image generation. Render wall time was not measured. Production hosted inference remains NOT TESTED. The remaining nine languages have no real open-model samples yet.

## 16 October 2026 — live Telugu Studio continuation

Project `4a58783bd08d4d488ec3ad0733514479` has five unchanged real, ready, approved images. The local process listeners were verified on Piper `127.0.0.1:5008`, API `127.0.0.1:8000`, and frontend `0.0.0.0:3003`. The preview, narration save and render used explicit `provider=piper`, `TTS_PROVIDER=piper`, and empty premium rates; Piper HTTP logs recorded one preview and five save synthesis requests (all HTTP 200). No paid speech fallback was selected.

| Stage | Status | Measured evidence |
| --- | --- | --- |
| Preview API | PASS | `POST /api/voice/preview` HTTP 200 in 5.245 s; `test_reports/p0-telugu-local/app-preview.mp3`, 58,558 bytes. |
| Persist narration | PASS | `POST /api/projects/4a58783bd08d4d488ec3ad0733514479/audio/ai` HTTP 200 in 17.226 s. Saved provider `piper`, `te_IN-padmavathi-medium` revision on all five scenes, 23.64 s; downloaded `test_reports/p0-telugu-local/saved-piper-narration.mp3`, 378,714 bytes, SHA-256 `2bd228521c03b123dfb5002009cc0f7990c6b2813d5c3f204abc51938a5ffc32`. |
| Render precondition | FAIL, repaired | First `POST /render` returned HTTP 400: `Review and approve the current script before rendering`. An old approved review fingerprint omitted the subsequently added `brief` field. `review_is_current` now accepts that exact legacy fingerprint only when `brief` is absent; changed idea or brief still invalidates it. No new AI review or script/image generation was run. The focused regression passed outside the sandbox (1 passed, 64 deselected); a prior in-sandbox attempt stalled and was interrupted. |
| New project render | PASS | Retry `POST /render` HTTP 200. `render_started` event `2026-10-15T18:30:37.930787Z`; `render_done` event `18:30:55.494191Z`: 17.563 s between events. New 23.61 s video path `vidbharat/videos/46057842e877488e9a6c7200aa1f29a5/ef1ae2556bdd4152acbb4ebb57f66023.mp4`; five approved images were reused. |
| Captions | PASS for generation and visible warning; BLOCKED for human synchronization review | Saved audio and render both report `estimated`. Render returned 11 SRT entries; extracted frames at 1 and 19 s visibly show Telugu burned captions. The same estimated-timing warning was visible in both browser Audio and Render steps. Fluent synchronization review remains. |
| MP4 file and audio identity | PASS | `test_reports/p0-telugu-local/new-piper-studio.mp4`, 3,018,029 bytes, SHA-256 `f0bf5f9236a591ef039b69c949e14ec3a8333ede95ef8a114f8c998407739b59`. Bundled FFmpeg decoded full video/audio. Decoded MP4 audio and saved Piper narration are each 23.615 s and correlate at 0.99999 over a middle five-second window; this is the newly saved narration, not the older render audio. |
| Media response and browser download | PASS | Inline `GET /api/media/...mp4` HTTP 200, `video/mp4`, no attachment header, 0.947 s. `?download=1` HTTP 200 with `Content-Disposition: attachment`, 0.928 s. The Studio MP4 link downloaded `C:/Users/gunak/Downloads/ef1ae2556bdd4152acbb4ebb57f66023.mp4` (3,018,029 bytes); SHA-256 matches the project export. |
| Browser Studio playback | PASS | The saved HTML audio player reached `readyState=4`, played with `paused=false`, and reported 23.614694 s. The browser Piper preview action returned `POST /api/voice/preview` HTTP 200 and Piper `/synthesize` HTTP 200; its button returned to idle without an error. The final HTML video player reached `readyState=4`, played with `paused=false` at 10.18 s, and reported 23.613991 s. |

The live browser initially returned project HTTP 404 because it was signed in under another account. The local project owner is the seeded `admin@vidbharat.ai` account; the account-specific 404 was not a backend outage. Signing in as that account opened the project. Local paid API/cloud charge for this test was ₹0; electricity was not metered. Fluent-speaker listening and human caption synchronization remain unverified. The older 15 October sections below are historical checkpoints.

The measured processing stages total **40.034 s** (preview 5.245 + narration save 17.226 + render-event interval 17.563). This excludes browser navigation, sign-in, diagnosis and download time; it is not an end-to-end wall-clock duration.

## 15 October 2026 — current session

| Check | Result | Limit |
| --- | --- | --- |
| `python -m py_compile ai.py projects.py server.py piper_tts.py tests/test_piper_tts.py` | Passed | Syntax only |
| `npm run build` in `frontend` | Passed | Build only, not browser behavior |
| `pytest tests/test_piper_tts.py tests/test_output_integrity.py -q` in `backend` | Stalled with no test output after 30 seconds; interrupted | Existing Windows async socket-pair issue; no test pass claimed |
| `pytest tests/test_piper_tts.py -k endpoint_configuration -q` | 1 passed | Configuration validation only; three async tests deselected |
| `pytest tests/test_piper_tts.py -k 'not sends_text_and_speed and not rejects_invalid_audio' -q` | 3 passed | Configuration, missing-service isolation and premium operator gate; two async protocol tests deselected |
| `pytest tests/test_piper_tts.py -q` outside sandbox | 5 passed | Mock HTTP service, not live synthesis |
| `pytest tests/test_piper_tts.py tests/test_output_integrity.py tests/test_beta.py -q` outside sandbox | 76 passed, 6 subtests | Mocked provider and workflow checks; no live narration |
| Full selected backend suite outside sandbox | 234 passed, 6 subtests | Includes Coach/project/audio regressions; mostly mocked providers |
| Full selected backend suite after premium gate and benchmark harness | 238 passed, 6 subtests | Current regression baseline; mocked providers, no live narration |
| `pytest tests/test_piper_tts.py -q` after manifest/cache tests | 8 passed | Includes noncommercial voice rejection, hidden UI availability, and model-revision cache invalidation |
| `pytest tests/test_piper_tts.py -q` after benchmark/premium tests | 11 passed | Current focused audio suite; mocked services and no paid inference |
| Frontend Jest suite outside sandbox | 13 passed across 2 suites | Includes Odia unavailable voice and explicit Piper preview/generation payload |
| `gcloud config get-value project` | Returned `ayana-video-studio` | Configuration only, not authenticated resource access |
| `gcloud auth list` | Failed: sandbox denied access to SDK `credentials.db` | Billing and quota not inspected |
| Read-only `gcloud auth list` and `gcloud billing projects describe` outside sandbox | Active account listed; billing request failed because token refresh requires interactive reauthentication | No current billing evidence |
| Frontend Jest suite inside sandbox | No tests executed: EPERM renaming Jest cache files | Re-run outside sandbox passed; not an application failure |
| Real Telugu Piper sample, `te_IN-padmavathi-medium` | Three MP3s generated through local Piper HTTP service and application adapter; 3.47 s, 10.32 s, 5.96 s audio; 3.300 s, 1.288 s, 0.779 s wall time | Windows CPU evaluation only; native-speaker review, production license compliance and app end-to-end flow pending |
| FFmpeg decode and signal check | All three MP3s decoded and contained non-silent audio (RMS 0.15472–0.20435) | Signal validity does not establish pronunciation or quality |
| Premium audio preflight and routing tests after budget gate | 11 focused backend tests passed; 5 tests with async service/temp fixtures deselected | The focused tests verify rate rounding, cap, missing budget, hidden unpriced provider, no network before authorization, and explicit provider behavior; no live premium call |
| Frontend audio and studio Jest after budget gate | 14 passed across 2 suites using a cache directory under `node_modules` | Mocked API; no browser or paid call |
| Frontend production build after budget gate | Passed | Bundle build only |
| `py_compile` and `git diff --check` after budget gate | Passed | Syntax and whitespace only |
| Backend selected run including `tmp_path` | 10 passed, 4 deselected, 1 setup error: sandbox could not create a pytest temp directory | Environment error before that test executed; full async suite not rerun in this turn |
| Cloud billing/quota verification | Not run | Authenticated cloud inventory not available in this session |
| Read-only RAM inspection | Automatic approval review rejected the command after the usage limit was hit; no command executed | Memory capacity remains unmeasured |
| `python -m pytest tests/test_audio_coverage.py tests/test_premium_tts.py -q` | 11 passed | Confirms all 11 app language IDs have the same three provisional probe cases, can be exposed through Studio metadata, and route explicit open speech without a paid fallback; mocked route only, no new live audio |
| `python backend/audio_coverage.py` | All 11 listed; Telugu `samples_recorded`, ten `corpus_ready`; primary and full-set sample-complete flags false | Reads local reports; it does not call models or score language quality |
| `python -m py_compile audio_eval_corpus.py audio_coverage.py benchmark_piper_audio.py piper_tts.py` and `git diff --check` | Passed | Syntax and whitespace checks only |
| Hugging Face local access check | `huggingface_hub.get_token()` returned false; no token content displayed | Cannot verify approval for gated Indic Parler weights without an authenticated account |
| Local compute check | 23.79 GiB total RAM, 6.08 GiB available; 3.80 GB free on `C:`; `torch` and `parler_tts` absent; `nvidia-smi` unavailable | VRAM not verified; full model/runtime load not attempted |
| Hugging Face HTTPS metadata request from shell | Failed with DNS `getaddrinfo failed` | No ONNX alternative or gated weights downloaded from this shell |
| Publisher's Indic Parler Hugging Face Space, Hindi short case | FAIL — page loaded in Chrome, but Generate Audio returned `Error: No API found` | No audio or latency evidence; hosted demo failure does not prove a self-hosted model fails |
| Telugu in-process `server.voice_preview` with local Piper and explicit provider | BLOCKED — first import logged Supabase DNS failure; second attempt used inert local DB configuration but no request reached the loopback service before interruption | No preview file saved and no app preview PASS claimed; local socket restrictions remain a risk |
| `gcloud auth list --format='value(status)'` | Failed with SDK `credentials.db` access denied in sandbox | Billing, GPU quota and available cloud compute remain unverified; prior external read-only billing query required interactive token refresh |
| `python -m pytest tests/test_piper_tts.py -k unaligned_open_speech -q` | 1 passed, 11 deselected | Confirms estimated/open captions are distinguished from verified word timing; full app narration and export not exercised |
| Frontend `npm run build` after estimated-caption notice | Passed | Compiles UI notice; not a browser playback or caption synchronization test |
| Backend async Piper cache test after status change | Stalled in sandbox and interrupted | No pass claimed; focused pure status test passed separately |
| Expanded selected backend audio run after caption fix | 14 tests printed progress, then stalled in sandbox and was interrupted | No completed-suite pass claimed; use the completed 11-test matrix/premium run and focused status result only |

Prior evidence: `test_reports/EDIT_JOURNEY_2026-10-15.md` reports 215 simulated workflow tests and seven in-process real database/API checks. `test_reports/FRESH_CLOUD_VIDEO_2026-10-15.md` reports that no fresh cloud video was produced. Neither proves live open TTS.

No paid model calls, deployments or cloud resources were initiated in this session. One roughly 64 MB Telugu Piper voice and an isolated CPU runtime were downloaded locally for the bounded evaluation. The generated samples and JSON report are in the ignored `test_reports/piper-audio-te-2026-10-15/` directory; full details are in `test_reports/PIPER_TELUGU_REAL_2026-10-15.md`. No other language has real open-model audio evidence yet.

The [11-language execution checkpoint](../test_reports/AUDIO_11_LANGUAGE_EXECUTION_2026-10-15.md) separates real sample, native review, app preview, caption and MP4 status per language. Its controlled cloud price is a published-rate planning example, not an actual charge.

## P0 Telugu exact-flow result — 15 October 2026

| Stage | Status | Actual evidence and timing |
| --- | --- | --- |
| Script | PASS | Three fixed Telugu scripts exist in `backend/audio_eval_corpus.py`; translation quality awaits fluent review. Script preparation time was not measured. |
| Open TTS | PASS | Existing Piper `te_IN-padmavathi-medium` generated three local MP3s in ignored `test_reports/piper-audio-te-2026-10-15/`. Wall times: 3.300, 1.288, 0.779 seconds. FFmpeg decoded all three. |
| Studio preview | BLOCKED | Earlier in-sandbox loopback request did not reach the Piper service; no preview playback or HTTP timing was captured. |
| Save narration | BLOCKED | Requires a running app with reachable database and an existing Telugu project; no saved project audio path or request timing captured. |
| Captions | BLOCKED | Code marks Piper word timing `estimated` and shows a review warning. No saved-project SRT, rendered caption playback or synchronization timing captured. |
| FFmpeg render | BLOCKED | Requires approved current script, real approved scene images and saved narration. No render job completed or timing captured. |
| MP4 playback/download | BLOCKED | No Telugu app MP4 exists; no downloaded path, ffprobe result or playback timing captured. |

The [controlled local PowerShell runbook](P0_TELUGU_CLOUD_RUNBOOK.md) is the next execution method. This table does not convert code paths or mocked tests into a PASS. Frontend Render copy was corrected to preserve the estimated-caption warning without suggesting Piper regeneration produces word timestamps.

An **isolated FFmpeg stage** now passes using the existing `te_short.mp3`, independent of the Studio project: two estimated caption chunks were burned onto a generated test image, the clip took 0.860 seconds and mux took 0.247 seconds. The output `test_reports/p0-telugu-local/isolated-render.mp4` is 84,849 bytes and 3.47 seconds, contains video and audio streams, and fully decoded with the application's bundled FFmpeg. A frame at 0.8 seconds shows Telugu caption glyphs. Its SRT and measured results are in the same ignored folder (`isolated-render.srt`, `render_probe.json`). This verifies the local FFmpeg/caption rendering primitive only; it does not change the **BLOCKED** app render, Studio playback, download or human synchronization statuses above. Local paid API/cloud charge was ₹0; local electricity was not metered.

The MP4 download path was changed to request an opt-in attachment header from `/api/media/...?download=1` because the frontend and backend dev ports are cross-origin and browsers may ignore an HTML `download` attribute alone. Inline preview keeps its previous response. The frontend production build and `git diff --check` passed. The focused backend test `test_media_download.py` stalled during app import in the sandbox, then **passed (1 test)** outside it. This is a mocked response check; no live browser download PASS is claimed. The controlled runbook was corrected after preflight found the backend `.venv` lacks Pillow and `ffprobe` is unavailable; it now uses the verified system Python and bundled FFmpeg.

Earlier cloud read-only attempt outside sandbox: `gcloud auth list --filter='status:ACTIVE'` returned an active account; `gcloud config get-value project` returned `ayana-video-studio`; `gcloud billing projects describe ayana-video-studio` failed before data retrieval with `Reauthentication failed. cannot prompt during non-interactive execution`. Authentication was subsequently restored; see the live audit below. No deployment, paid inference or billing update was made.

Indic Parler public model-card check: gate, Apache-2.0 model license and 0.9B F32 size PASS as public metadata; accepted account terms, authenticated weights, training-data commercial rights, measured memory, local/cloud inference and per-language output remain BLOCKED. The card gives no measured minimum host specification. Existing 11-language matrix remains unchanged.

Final P0 edit checks: `npm run build` in `frontend` compiled successfully after the Render caption-warning correction; `git diff --check` exited 0. These check compilation and whitespace only, not the Telugu browser journey.

## Authenticated read-only cloud audit — 15 October 2026

| Check | Result | Limit |
| --- | --- | --- |
| `gcloud billing projects describe` and `billing accounts describe` | PASS — project billing enabled; account `01AFD8-B12EEE-80C32E` open, INR | No trial, remaining credit or expiry field returned. Founder independently supplied the same project billing result. |
| `gcloud run services list/describe`, jobs list | PASS — one ready `vidbharat-image-worker` in `asia-south1`, CPU 1/512Mi; zero jobs | No GPU service configured; founder independently supplied the service listing. |
| Compute project and Mumbai regional quota describe | PASS — project-wide `GPUS_ALL_REGIONS` limit 0; regional L4 limit 1, usage 0 | Quota conflict means no verified provisioning route; no creation attempted. |
| Service Usage Cloud Run GPU quota GET | PASS — L4 quota metric exists for Mumbai, but effective/default limit fields absent | Cannot claim available Cloud Run GPU quota. |
| Service Usage Vertex AI quota GET | PASS — Mumbai custom model serving L4 limit 1, T4 limit 1 | Quota is not actual capacity or free-trial billing eligibility. |
| Enabled APIs, resources and buckets | PASS — Vertex, Compute, Run, Storage, Artifact Registry and speech APIs enabled; four buckets, one Docker repository; no Compute VMs/disks or Mumbai Vertex endpoints/jobs | Listing did not call paid inference or modify resources. |
| Billing Overview browser read | BLOCKED — Google requested a fresh password in the in-app browser | Password was not entered; trial status and credits remain unknown. |

Full observed values and sources: [cloud audit](CLOUD_READ_ONLY_AUDIT_2026-10-15.md). No cloud resource, billing, IAM or API setting changed.

## Controlled local Studio attempt — 15 October 2026

| Stage | Status | Actual result |
| --- | --- | --- |
| Piper server | PASS | Existing `te_IN-padmavathi-medium` server started on `127.0.0.1:5008` outside the sandbox. No synthesis call in this attempt. |
| API startup | PASS | Existing FastAPI app started on `127.0.0.1:8000` with `TTS_PROVIDER=piper` and `TTS_PREMIUM_RATES_JSON={}`. |
| Local login | PASS | `POST /api/auth/login` returned HTTP 200 using existing `.env` credentials in process memory; no credentials printed. |
| Project list | PASS | `GET /api/projects` returned HTTP 200. It listed two approved Telugu projects with five scenes each; one showed five real ready approved images. Script-review currency and download eligibility were not checked. |
| Studio preview onward | BLOCKED | Before the next project inspection or browser step, automatic approval review rejected unsandboxed command execution because the host usage limit was reached. The rejected command was not executed. No preview, save, warning, app render, or browser download response exists. |

The first failing dependency in this controlled attempt is the **host's automatic approval review**, not an app endpoint. Its stated reason was a usage limit and it gave a next-review time of 16 October 2026 00:55 local. The earlier login and project-list endpoints returned 200; there is no failed app endpoint to report. The two foreground command sessions were no longer addressable when cleanup was attempted. Do not treat that as proof of process shutdown; check ports 5008 and 8000 before restarting. No paid speech provider was selected or called.
