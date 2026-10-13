# Limited cloud beta preparation

Status: deployment files prepared, not deployed. Image build, cloud credentials,
bucket access and HTTPS must pass before inviting users. No model was trained.

## Local checks

Run the frontend on port 3003 and API on 8000. The cloud image builds the frontend
with `/api` on the same origin and serves it through FastAPI. Do not use the local
development build unchanged in production; it targets localhost.

## Hosting choice for this beta

For local creator testing before the full deployment, `image-worker/` provides
a small Cloud Run bridge to Vertex AI. It lets the local backend generate real
scene images without installing Google Cloud credentials on the laptop. The
bridge has no GPU and does not move the frontend, database or video renderer.
See `image-worker/README.md` for its rollout and cost controls.

Use one always-running Google Compute Engine VM with Docker Compose, HTTPS via
Caddy, and a private GCS bucket. The existing application uses process-local
background tasks. Do not put this version on scale-to-zero hosting or run multiple
API workers: tasks can be lost or duplicated. A durable task queue remains a
requirement before autoscaling. Interrupted jobs may currently require manual
status recovery; this limits the beta to supervised testing.

The VM runs API/rendering work; current AI generation calls remote providers.
No GPU or model weights are required for this existing pipeline. Future open-model
inference and tuning use separately provisioned cloud GPU workers.

## Before deployment

1. Choose project, region and beta domain. Confirm billing/credits and a spending
   limit. Enable the necessary cloud services and create an Artifact Registry repo.
2. Create a private bucket with uniform bucket-level access and public access
   prevention. Give only the VM service account the required object read/create
   access on this bucket. Use attached credentials, not a downloaded JSON key.
   With `IMAGE_PROVIDER=vertex`, that service account also needs permission to
   call Vertex AI in `ayana-video-studio`. Enabling the API alone does not grant
   the app's current Gemini API key access to Vertex; verify one authenticated
   Cloud Shell request before provisioning the worker. The VM must use its
   attached service account for image calls, not a pasted user access token.
3. Keep the configured database; verify the schema and database network access.
   This repository does not provision/migrate that existing database.
4. Supply an actual image name to Cloud Build's `_IMAGE` substitution. Review
   `.gcloudignore` and `.dockerignore` before uploading the source; secrets, media and evaluation
   reports are excluded. Cloud Build is billable and has not been started here.
5. On the VM, copy `beta.env.example` to `beta.env` and supply secrets securely.
   Restrict its permissions. Set `BETA_IMAGE` and `BETA_DOMAIN` for Compose.
   Point DNS at the VM; expose only HTTPS/HTTP externally, never port 8000 or a DB.
6. Start Compose on the VM. Check `/api/health`, login, project isolation, real
   scene generation, voice, render, download and a restart. Do not advertise the
   health endpoint as database/provider readiness.

Registration is closed by default. Initially use only the owner's beta account;
an invitation-management flow is not implemented. No bulk user import is included.
GCS mode does not copy old laptop media. Old projects need an explicit migration;
new test projects write to the bucket. Keep a backup of the database and media.

## Model improvement and fine-tuning

`backend/evaluate_beta.py` exercises the live API with synthetic test scenarios.
`--improve` records the model's response to editorial feedback. This changes the
output, not the model's weights. Native speakers must review the result.

For actual tuning, prepare human-corrected examples in the chosen provider's
format, separate training and held-out evaluations, then choose a supported model
and cloud training budget. An API key alone is not a fine-tuning setup. Do not
automatically train on existing customer projects or self-generated ratings.

Prepare explicit reviewed JSONL rows with `backend/prepare_tuning_data.py`.
Required fields are `split` (`train` or `validation`), `prompt`, `response`,
`reviewed: true` and `permission_to_train: true`. Pass an input file and a new
output directory. The helper rejects duplicate prompts and unreviewed examples.
Review similarity across examples manually as well; exact duplicate detection
cannot identify paraphrased leakage. No ready training corpus exists yet.

## Release limitations

This beta remains the existing image-animation studio. Full ten-language UI,
motion generation, lip sync, thumbnails, publishing, durable jobs and cost/quota
enforcement are not complete. Keep the beta private until access and spending
controls are ready. GPU fine-tuning and public launch are not part of this deployment.
