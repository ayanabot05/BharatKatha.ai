# First private BharatKatha Telugu video: next approval

## Verified progress

### Production migration and deployment authorization update

After the explicit four-step approval request, the founder instructed "continue". The approved scope is migration 002, private API/scene/render deployment, scoped Job invocation, and one 30–45-second Telugu video test. The founder then ran the checksum- and project-guarded transactional migration command and supplied `SUCCESS: migration 002 committed; both lease columns verified.` Production migration 002 is now completed on founder-supplied evidence; do not rerun it. API startup creates the configured admin account if absent or synchronizes its password with the supplied admin secret if it differs. API deployment remains the next step, using the existing immutable image.

### Infrastructure and first cloud voice evidence

Founder-supplied outputs confirm both private Mumbai STANDARD buckets, four dedicated runtime accounts, and version 1 of JWT/admin-email/admin-password secrets. API has secretAccessor on those three secrets and database-url. API/scenes/render have media-bucket objectUser; Piper has model-bucket objectViewer; scenes has project aiplatform.user. API Vertex access, API media bucket metadata access, image-token secret access, scenes/render database/JWT access, and scoped service/job invocation are not yet evidenced as complete.

The founder also deployed Piper revision `bharatkatha-piper-te-00001-6ss` using the successful digest, CPU 1 / RAM 1 GiB, min 0 / max 1, concurrency 1, private access. URL: `https://bharatkatha-piper-te-945043002954.asia-south1.run.app`. GCS prefix `padmavathi` contains the ONNX and JSON; source ONNX SHA-256 matches the worker's pinned value. A separate unused `venkatesh` prefix exists and is preserved.

An authenticated POST `/synthesize` returned HTTP 200 and RIFF/WAVE PCM 16-bit mono 22050 Hz in `/tmp/bharatkatha-voice-test.wav` in Cloud Shell. This is real remote Telugu synthesis evidence, not yet listening quality, persistent application audio, captions or MP4 evidence. Earlier GET `/` returned HTML; the existing API adapter already correctly POSTs `/synthesize` and uses an identity token with the service origin as audience. No client code change or rebuild is needed for that endpoint.

The latest supplied regional Job listing was empty. Production migration, main API deployment and renderer/scene Job deployment remain unverified/unapproved in this thread. Piper deployment was performed by the founder; it does not extend the agent's infrastructure-only authorization. The repository-level MIT tag shown by the founder is not a substitute for the exact voice card and Piper runtime license notices. Preserve the earlier model-specific license record.

### Completed worker builds (founder-supplied Cloud Shell results)

- Piper corrected build `a0a5eabe-a344-4b48-8334-dac14c7f0eac`: SUCCESS, 2026-10-16 08:15:49.408390728Z to 08:16:58.514379Z (69.1 s). Image `asia-south1-docker.pkg.dev/ayana-video-studio/vidbharat-beta/voice-piper-te@sha256:573b474a014d231c1e355d4fb35a95773fd536a9d6ed325afb766137e4110b5d`.
- Renderer build `1907cd46-75ae-4ad4-9961-1b950cf86d1b`: SUCCESS, 2026-10-16 08:17:38.472661700Z to 08:19:50.883691Z (132.4 s). Image `asia-south1-docker.pkg.dev/ayana-video-studio/vidbharat-beta/render-worker@sha256:440041622f9f76040eccd21bfd2cedaffa7802f7797d287f44a395e7e24080ec`.
- Gross elapsed-time compute estimate at $0.006/min: Piper retry $0.00691, renderer $0.01324; all three successful builds approximately $0.02712. The failed Piper attempt, storage/logs/transfer and any free allowance are excluded. Actual billed cost is unavailable.
- API, Piper and renderer images are built and pushed; inference, runtime startup, job execution and MP4 generation remain unverified. Earlier pending-build requests below are historical and superseded by these outcomes. No deployment, production migration or IAM change is authorized by the build results.

Founder-supplied Cloud Shell results confirm migration 002's rollback rehearsal passed against restored PostgreSQL 17.11 with 44 project rows and unchanged fingerprint `deaf9f6edda11b7049a649bdefb8cfed`. No repeat database check is needed for the next build stage.

Main API build `95bf4e39-7d88-497f-95f9-d85ab0424bfb` returned SUCCESS. Start: `2026-10-16T07:59:00.897594195Z`; finish: `2026-10-16T08:00:10.599231Z`; elapsed 69.7 seconds. The immutable image to reuse for API and scene Job is:

`asia-south1-docker.pkg.dev/ayana-video-studio/vidbharat-beta/main-api@sha256:3ce2bd16330c8ed57e8cfd81cf72644288fae5ee256f6232398e8bca17e36f83`

Estimated gross build compute is $0.00697 at the default-pool $0.006/min rate, before free allowance, storage/logs/transfer. Actual billed cost is unavailable. Build success does not establish runtime readiness. No live migration, deployment, IAM change or worker build is approved by this result.

## Immediate approval requested: two worker builds only

### Piper build failure and prepared fix

Founder-supplied log for build `b138d989-a182-4047-adb3-3a53bf8721b2` shows Python dependencies installed successfully, then Docker step `useradd --create-home voice` failed with exit 9 because Debian already contains group `voice`. The last overall status supplied was WORKING with failureInfo; terminal status/duration must still be collected. No successful image digest was supplied.

The local Piper Dockerfile now uses `useradd --create-home --gid voice voice`, explicitly reusing that existing group. USER remains `voice`. A byte-for-byte patch check against the uploaded source archive passed. Old Dockerfile SHA-256: `fe0b27e7d10dfe57719efdf3e94ad5a4ebe861f5ee19ce1ee151f3537b95801d`; corrected SHA-256: `535e796d189bb371cfc2a9894e355219fa1f472ae04e04a434b15a6d0bb40a99`. No local container runtime is available and no corrected cloud build has run. Apply the guarded one-line correction and update the per-file manifest in Cloud Shell before a separately approved retry. The original ZIP/checksum below remains the original failing source snapshot, not a corrected archive.

Prepared archive: `deliverables/bharatkatha-telugu-workers-build-20261016.zip`, 63 files, 1,115,382 bytes; SHA-256 `5e64a4ed581143e369335dc7b8d11f71664129e0268e784ca4bdfc8037396a2b`.

Local checks passed: ZIP round-trip, per-file checksum manifest, every backend file byte-identical to the successful API build source, configured credential values excluded, and two one-step Docker build configs each with a 1800-second timeout. No model weights or generated media are packaged. No application code changed.

| Build | CPU / RAM | Timeout | Gross compute estimate |
| --- | --- | --- | --- |
| Telugu Piper | Default pool 2 vCPU / 8 GB | 30 minutes | $0.03–$0.12 if 5–20 minutes; $0.18 at timeout |
| FFmpeg renderer | Default pool 2 vCPU / 8 GB | 30 minutes | $0.03–$0.12 if 5–20 minutes; $0.18 at timeout |

Total compute at both timeouts: $0.36, plus storage/logs/transfer; not a spending cap. Actual duration and any free allowance are unknown. Pricing: https://cloud.google.com/build/pricing . Build Piper first; inspect its result before submitting renderer. Do not automatically retry a failed or ambiguous submission. These builds create image artifacts only; recovery is to leave an unsuccessful candidate unused. Retained source/images can incur storage charges. No existing serving resource changes.

After explicit approval and upload, verify archive SHA-256, extract into `$HOME/bharatkatha-telugu-workers-build-20261016`, and run `sha256sum --check SOURCE_SHA256SUMS` from that directory. Then submit exactly these separately, not the broad `release.sh build` action:

```bash
gcloud builds submit "$HOME/bharatkatha-telugu-workers-build-20261016" --project=ayana-video-studio --region=asia-south1 --config="$HOME/bharatkatha-telugu-workers-build-20261016/deploy/voice-piper/cloudbuild.yaml" --timeout=30m --substitutions="_IMAGE=asia-south1-docker.pkg.dev/ayana-video-studio/vidbharat-beta/voice-piper-te:review-20261016" --async --quiet
```

```bash
gcloud builds submit "$HOME/bharatkatha-telugu-workers-build-20261016" --project=ayana-video-studio --region=asia-south1 --config="$HOME/bharatkatha-telugu-workers-build-20261016/deploy/render-worker/cloudbuild.yaml" --timeout=30m --substitutions="_IMAGE=asia-south1-docker.pkg.dev/ayana-video-studio/vidbharat-beta/render-worker:review-20261016" --async --quiet
```

Record each build ID, terminal status, image digest, timestamps and available cost evidence. API and Supertonic builds are outside this approval.

## Subsequent deployment approval: smallest Telugu path

| Runtime | Allocation | Scaling / limit |
| --- | --- | --- |
| Private `bharatkatha-api` | 1 vCPU / 1 GiB | min 0, max 2, concurrency 10, request timeout 900 s |
| Private `bharatkatha-piper-te` | 1 vCPU / 1 GiB | min 0, max 1, concurrency 1, timeout 300 s |
| `bharatkatha-scenes` Job | 1 vCPU / 1 GiB; reuse API digest | 1 task, parallelism 1, 20-minute timeout, retries 0 |
| `bharatkatha-render` Job | 2 vCPU / 2 GiB | 1 task, parallelism 1, 20-minute timeout, retries 0 |
| Existing image worker | Preserve deployed configuration | Invoke existing endpoint only |

New services have zero idle instance compute at min=0. Job parallelism does not limit concurrent executions; the private test must submit one project only. Cold-start time, model download and inference memory are still unmeasured. Planning allowance remains about $0.52 for a five-image video, including Vertex calls, compute, retries, storage and download; it is not a quote or cap. Do not broaden to Hindi/English until the Telugu MP4 works.

Deployment prerequisites to resolve after builds: approved private STANDARD Mumbai media/model bucket locations; the pinned Telugu model and JSON staged cloud-to-cloud with hash/notice checks; enabled required secret versions; dedicated API, scene, Piper and renderer service accounts and scoped permissions; separate approval for production migration 002; actual private HTTPS worker URL and Piper manifest. Use `TTS_PROVIDER=piper` for this Telugu-only private stage. Cloud Run invocation must use identity tokens; API Job execution needs scoped execution-with-overrides permission, and jobs need their own GCS/database access. No permission changes are authorized yet.

The old all-language `release.sh` is broader than this stage: do not execute its prepare/build/deploy/configure actions unchanged. Prepare the exact scoped deployment commands after actual worker digests and resource metadata are known. No API rebuild is needed for the scene Job. Leave the existing image worker and Growth Coach unchanged.

After separately approved deployment/migration/IAM and successful startup checks, use a private cloud client to create one 30–45-second Telugu project, generate the script and images, invoke Piper, render captions and MP4 in the Job, and verify GCS artifacts, playback/download and worker execution logs. Runtime evidence and an actual MP4 are the success gate. First-deployment recovery is to stop new submissions and any active test executions, retain artifacts for diagnosis, and leave services private at min=0. Do not drop lease columns while jobs are active; data-producing executions cannot be undone by dropping columns.
