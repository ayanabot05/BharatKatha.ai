# BharatKatha cloud deployment approval packet — 16 October 2026

**Superseded by [the scale-to-zero revision](CLOUD_DEPLOYMENT_APPROVAL_REVISED_2026-10-16.md).** The original always-on API cost and commands below must not be used for approval. The founder subsequently confirmed `bharatkatha-database-url` exists and created a separate backup bucket; the older inventory below is historical.

Status: prepared, **not deployed or cloud validated**. All new billable actions below require the founder's explicit approval of this configuration. No GPU is proposed.

## Fresh inventory and location

The founder's 16 October Cloud Shell output and a fresh read-only Google API check agree: billing is enabled on `ayana-video-studio`; `asia-south1` has only `vidbharat-image-worker`, no Cloud Run Jobs, and Artifact Registry repository `vidbharat-beta`. Four buckets exist. `ayana_video_studio` is ASIA NEARLINE, `ayana-video-studio-voice-eval-20261014` is Mumbai STANDARD with a seven-day delete lifecycle, `ayana-video-studio-training-945043002954` is Mumbai STANDARD but designated for training, and `ayana-video-studio_cloudbuild` is US STANDARD. None is an appropriate persistent production media bucket. Recommend a new **STANDARD, asia-south1, uniform-access, public-access-prevented** bucket such as `bharatkatha-prod-media-945043002954`, after approval. Keep existing buckets and their contents intact. The two listed secrets are `indic-parler-hf-token` and `vidbharat-image-worker-token`; no production DB/JWT/admin secrets are listed.

## Proposed resources for approval

| Resource | CPU / RAM | Min / max instances | Concurrency / timeout | Planning billable time per video | Gross idle cost, 30 days |
| --- | --- | --- | --- | --- | --- |
| `bharatkatha-api` Cloud Run, private at first | 1 vCPU / 1 GiB | 1 / 1 | 10 / 900 s | continuous; script and image preparation still include in-process tasks | about **US$51.84/month** before shared free tier |
| `bharatkatha-piper-te` private Cloud Run | 1 vCPU / 1 GiB | 0 / 1 | 1 / 300 s | 90 s including model cold start, assumption | $0 |
| `bharatkatha-hindi-hi` private Cloud Run, shared Hindi/English model | 2 vCPU / 2 GiB | 0 / 1 | 1 / 300 s | 300 s including model cold start, assumption for either language | $0 |
| `bharatkatha-render` Cloud Run Job | 2 vCPU / 2 GiB | 0 / 1 task **per execution** | 1 task / 20 min / 0 automatic retries | 180 s including cold start, assumption | $0 |
| Existing `vidbharat-image-worker` | 1 vCPU / 512 MiB observed | existing configuration, max 1 | existing | usage unmeasured | unchanged |
| New production media bucket, STANDARD Mumbai | storage | not applicable | private | 15 MiB of assets kept per video; one 5 MiB download | no empty-bucket storage charge |

**Concurrency caveat:** a Job's `--parallelism 1` limits one execution, not the number of simultaneous executions. The API's daily beta quota and one API instance reduce load but do not hard-cap total concurrent render executions. Add a durable queue or explicit execution cap before broad public traffic. Keeping one API instance with allocated CPU is a temporary measure for existing in-process scene generation; a restart can still interrupt a scene task. This is a controlled-beta reliability blocker, not full asynchronous durability.

**Estimated gross infrastructure costs (USD, before free tier, taxes, billing-account adjustments):** Cloud Run Mumbai list rates: instance billing $0.000018 per vCPU-s and $0.000002 per GiB-s; request billing $0.000024 per vCPU-s and $0.0000025 per GiB-s. With equal Telugu/Hindi/English mix, Telugu voice $0.002385/video, Hindi or English through the same Supertonic worker $0.0159/video, and render $0.0072/video. Add about $0.0003 per video-month for 15 MiB STANDARD storage and a **planning allowance** of $0.0006 for one 5 MiB browser download at $0.12/GiB. About $0.0195/video plus $51.84/month for the API. [Cloud Run prices](https://cloud.google.com/run/pricing), [Cloud Storage prices](https://cloud.google.com/storage/pricing). Internet egress billing follows destination/SKU; $0.12/GiB is an assumption to replace with observed invoice data.

| Videos/month | API base | Voice + render + storage + one download | Gross planning total |
| ---: | ---: | ---: | ---: |
| 100 | $51.84 | about $1.95 | **$53.79** |
| 500 | $51.84 | about $9.75 | **$61.59** |
| 1,000 | $51.84 | about $19.50 | **$71.34** |

These are **not full cost per video**: they exclude existing image-worker and Vertex/Gemini image/text charges, Supabase, Vercel, Speech-to-Text where used, Cloud Logging, retries, extra downloads, build/storage artifacts, and unknown Hindi model load time. Four 20-minute default-pool e2-medium image builds would add up to about $0.24 at list price before any free tier; actual build time is unknown. Cold starts are included only through the assumed 90/300/180-second billable durations. Actual costs require timed live cloud generations in each language and billing export or metrics. [Cloud Build prices](https://cloud.google.com/build/pricing).

## Identity, assets, secrets, and routes

Create dedicated service accounts `bharatkatha-api`, `bharatkatha-piper`, `bharatkatha-hindi`, and `bharatkatha-render`. Grant API and render identities bucket-scoped `roles/storage.objectUser` on the new media bucket, plus the minimum bucket metadata permission needed for `/api/ready` (`roles/storage.bucketViewer` on that bucket). Give voice identities `roles/storage.objectViewer` only on the private model bucket; for tighter least privilege stage the two models in separate buckets. Give the API `roles/run.invoker` on each private voice service, and `roles/run.jobsExecutorWithOverrides` on only the render job. Give each runtime only its needed Secret Manager `roles/secretmanager.secretAccessor` grants. The API's existing image-worker token secret must be readable by the API identity; the image worker itself remains unchanged. The API also needs `roles/aiplatform.user` for Vertex text and access to any image-worker invocation mechanism already in use. The deployer needs Artifact Registry writer, Cloud Build editor/build permissions, Cloud Run admin, service account user, bucket/IAM admin, and Secret Manager admin for setup; prefer scoped grants. The model and media buckets must keep public access prevention enforced.

Historical secret list: `bharatkatha-database-url`, `bharatkatha-jwt-secret`, `bharatkatha-admin-email`, `bharatkatha-admin-password`. The founder subsequently confirmed the database secret exists and the incorrectly named database secret was deleted; other names remain unverified. Existing `vidbharat-image-worker-token` is reused. Do not put secret values in repo, command line, logs, or this document. Supabase DB schema compatibility and TLS connection must be checked before API deploy. Required private GCS objects: pinned Telugu `te_IN-padmavathi-medium.onnx` and `.json`, with ONNX SHA-256 `414aa596...f3c2cfa57d`, and pinned Supertonic 3 model revision `aafc6e3...efc49d7fe4ce6d46` including its `LICENSE`, ONNX and M1 style files. Stage from Cloud Shell or cloud source; do not transfer through the founder laptop. Piper runtime GPLv3 and Telugu voice attribution, and Supertonic OpenRAIL-M obligations need a final commercial/license review. The video renderer already discloses Supertonic AI narration.

Private Cloud Run voice calls use HTTPS and Google-signed ID tokens whose audience is the service URL. Render dispatch uses ADC to call `https://run.googleapis.com/v2/...:run` with a job-specific IAM grant. The job rechecks project owner and `rendering` state before reading DB/GCS, then stores MP4/SRT state in GCS/DB. The public media endpoint is user authenticated. The proposed API starts private; exposing it to Vercel and setting exact `FRONTEND_URL` require a successful smoke test. No deployment URL for the new resources exists yet.

The previous English implementation used `edge-tts` with `en-IN-NeerjaNeural`/`en-IN-PrabhatNeural`. It is now disabled in production because commercial rights for the Edge consumer route are not established. The pinned Supertonic 3 M1 worker now accepts both `hi` and `en`; its publisher lists English support. This adds no new third-party paid service or model weight. English quality, latency and caption output through this route have **not** been tested on Cloud Run, so **English readiness is still blocked**. [Supertonic supported languages](https://huggingface.co/Supertone/supertonic-3), [Microsoft paid TTS output rights](https://www.microsoft.com/licensing/terms/en-US/productoffering/MicrosoftAzure/allprograms).

## Cloud Shell sequence

Read-only inventory, with no secret values:

```bash
cd /path/to/BharatKatha.ai
bash deploy/cloud-shell/read-only.sh
gcloud storage buckets describe gs://ayana-video-studio-training-945043002954 --format='yaml(location,storageClass,iamConfiguration,lifecycle)'
gcloud storage buckets describe gs://ayana-video-studio-voice-eval-20261014 --format='yaml(location,storageClass,iamConfiguration,lifecycle)'
gcloud storage buckets describe gs://ayana_video_studio --format='yaml(location,storageClass,iamConfiguration,lifecycle)'
```

**After explicit approval only:** create the production STANDARD bucket, service identities, secret entries/versions through a secure Console or stdin flow, bucket/object IAM, then build/deploy. These are billable or alter security state. Verify the exact `FRONTEND_URL`, model staging, image worker token behavior, and IAM before running. The script deploys resources privately and stops before public Vercel connection:

```bash
cd /path/to/BharatKatha.ai
gcloud storage buckets create gs://bharatkatha-prod-media-945043002954 --project=ayana-video-studio --location=asia-south1 --default-storage-class=STANDARD --uniform-bucket-level-access --public-access-prevention
gcloud iam service-accounts create bharatkatha-api --project=ayana-video-studio
gcloud iam service-accounts create bharatkatha-piper --project=ayana-video-studio
gcloud iam service-accounts create bharatkatha-hindi --project=ayana-video-studio
gcloud iam service-accounts create bharatkatha-render --project=ayana-video-studio
# Add secret values only through a secure Console or protected stdin procedure.
# These binding commands are needed before and after deploy respectively:
API_SA=bharatkatha-api@ayana-video-studio.iam.gserviceaccount.com
RENDER_SA=bharatkatha-render@ayana-video-studio.iam.gserviceaccount.com
PIPER_SA=bharatkatha-piper@ayana-video-studio.iam.gserviceaccount.com
HINDI_SA=bharatkatha-hindi@ayana-video-studio.iam.gserviceaccount.com
for SA in "$API_SA" "$RENDER_SA"; do
  gcloud storage buckets add-iam-policy-binding gs://bharatkatha-prod-media-945043002954 --member="serviceAccount:$SA" --role=roles/storage.objectUser
done
gcloud storage buckets add-iam-policy-binding gs://bharatkatha-prod-media-945043002954 --member="serviceAccount:$API_SA" --role=roles/storage.bucketViewer
for SA in "$PIPER_SA" "$HINDI_SA"; do
  gcloud storage buckets add-iam-policy-binding gs://YOUR_APPROVED_PRIVATE_STANDARD_MODEL_BUCKET --member="serviceAccount:$SA" --role=roles/storage.objectViewer
done
for NAME in bharatkatha-database-url bharatkatha-jwt-secret bharatkatha-admin-email bharatkatha-admin-password vidbharat-image-worker-token; do
  gcloud secrets add-iam-policy-binding "$NAME" --member="serviceAccount:$API_SA" --role=roles/secretmanager.secretAccessor
done
for NAME in bharatkatha-database-url bharatkatha-jwt-secret; do
  gcloud secrets add-iam-policy-binding "$NAME" --member="serviceAccount:$RENDER_SA" --role=roles/secretmanager.secretAccessor
done
gcloud projects add-iam-policy-binding ayana-video-studio --member="serviceAccount:$API_SA" --role=roles/aiplatform.user
export BHARATKATHA_DEPLOYMENT_APPROVED=yes
export FRONTEND_URL=https://YOUR_VERIFIED_VERCEL_DOMAIN
export MEDIA_BUCKET=bharatkatha-prod-media-945043002954
export MODEL_BUCKET=YOUR_APPROVED_PRIVATE_STANDARD_MODEL_BUCKET
export PIPER_MODEL_PREFIX=YOUR_STAGED_PINNED_TELUGU_PREFIX
export HINDI_MODEL_PREFIX=YOUR_STAGED_PINNED_HINDI_PREFIX
bash deploy/cloud-shell/deploy-after-approval.sh
gcloud run services add-iam-policy-binding bharatkatha-piper-te --region=asia-south1 --member="serviceAccount:$API_SA" --role=roles/run.invoker
gcloud run services add-iam-policy-binding bharatkatha-hindi-hi --region=asia-south1 --member="serviceAccount:$API_SA" --role=roles/run.invoker
gcloud run jobs add-iam-policy-binding bharatkatha-render --region=asia-south1 --member="serviceAccount:$API_SA" --role=roles/run.jobsExecutorWithOverrides
gcloud run services describe bharatkatha-piper-te --region=asia-south1 --format='value(status.url)'
gcloud run services describe bharatkatha-hindi-hi --region=asia-south1 --format='value(status.url)'
```

Then read actual URLs with `gcloud run services describe`, grant per-service `roles/run.invoker` and per-job `roles/run.jobsExecutorWithOverrides` to the API SA, update the API with actual `PIPER_VOICES_JSON`, `SUPERTONIC_HINDI_SERVICE_URL`, and `CLOUD_RENDER_JOB`, test authenticated worker and render calls, check logs, and only then permit unauthenticated access to the API and point Vercel to it. Do not infer success from a queued Cloud Build command; inspect build result, revision readiness and live responses.

## Verification state and launch blockers

Local Python syntax checks, focused tests and frontend production build passed (see `docs/TEST_RESULTS.md`). Docker was unavailable on the local Windows host, so **no Linux image build succeeded yet**. No remote voice request, Cloud Run Job execution, public frontend generation, MP4 playback/download or disconnected-laptop proof has passed. The model objects, new bucket, four new secrets, dedicated IAM grants and exact Vercel production origin are missing or unverified. English usage rights and the in-process image task failure mode remain release blockers. After approval: deploy API first, voices and render next, then complete live Telugu/Hindi/English videos from Vercel and measure timings, logs, GCS persistence, captions, playback and download while the founder laptop is disconnected.
