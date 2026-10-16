#!/usr/bin/env bash
# Cloud Shell: bash deploy/cloud-shell/release.sh prepare|build|deploy|authorize|configure|verify|publish|rollback
# Every action is gated by the founder's explicit approval.
set -euo pipefail
test "${BHARATKATHA_DEPLOYMENT_APPROVED:-}" = yes || { echo 'Deployment approval required' >&2; exit 2; }
ACTION="${1:?Choose prepare, build, deploy, authorize, configure, verify, publish or rollback}"
PROJECT=ayana-video-studio
REGION=asia-south1
REPO="${REGION}-docker.pkg.dev/${PROJECT}/vidbharat-beta"
TAG="${RELEASE_TAG:?Set one immutable release tag}"
API_IMAGE="${REPO}/main-api:${TAG}"
PIPER_IMAGE="${REPO}/voice-piper-te:${TAG}"
HINDI_IMAGE="${REPO}/voice-supertonic-hi:${TAG}"
RENDER_IMAGE="${REPO}/render-worker:${TAG}"
SA_SUFFIX="@${PROJECT}.iam.gserviceaccount.com"
gcloud config set project "$PROJECT" >/dev/null

case "$ACTION" in
  prepare)
    : "${MEDIA_BUCKET:?Approved STANDARD Mumbai media bucket required}"
    : "${MODEL_BUCKET:?Approved private STANDARD Mumbai model bucket required}"
    for NAME in api scenes piper hindi render; do
      gcloud iam service-accounts describe "bharatkatha-${NAME}${SA_SUFFIX}" >/dev/null 2>&1 ||
        gcloud iam service-accounts create "bharatkatha-${NAME}" --display-name "BharatKatha ${NAME} runtime"
    done
    for BUCKET in "$MEDIA_BUCKET" "$MODEL_BUCKET"; do
      gcloud storage buckets describe "gs://${BUCKET}" >/dev/null 2>&1 ||
        gcloud storage buckets create "gs://${BUCKET}" --project "$PROJECT" \
          --location "$REGION" --default-storage-class STANDARD \
          --uniform-bucket-level-access --public-access-prevention
    done
    for NAME in bharatkatha-database-url bharatkatha-jwt-secret bharatkatha-admin-email bharatkatha-admin-password vidbharat-image-worker-token; do
      gcloud secrets describe "$NAME" >/dev/null
    done
    for NAME in api scenes render; do
      gcloud secrets add-iam-policy-binding bharatkatha-database-url --member "serviceAccount:bharatkatha-${NAME}${SA_SUFFIX}" --role roles/secretmanager.secretAccessor >/dev/null
      gcloud secrets add-iam-policy-binding bharatkatha-jwt-secret --member "serviceAccount:bharatkatha-${NAME}${SA_SUFFIX}" --role roles/secretmanager.secretAccessor >/dev/null
    done
    for NAME in bharatkatha-admin-email bharatkatha-admin-password vidbharat-image-worker-token; do
      gcloud secrets add-iam-policy-binding "$NAME" --member "serviceAccount:bharatkatha-api${SA_SUFFIX}" --role roles/secretmanager.secretAccessor >/dev/null
    done
    gcloud secrets add-iam-policy-binding vidbharat-image-worker-token --member "serviceAccount:bharatkatha-scenes${SA_SUFFIX}" --role roles/secretmanager.secretAccessor >/dev/null
    for NAME in api scenes; do
      gcloud projects add-iam-policy-binding "$PROJECT" --member "serviceAccount:bharatkatha-${NAME}${SA_SUFFIX}" --role roles/aiplatform.user >/dev/null
      gcloud storage buckets add-iam-policy-binding "gs://${MEDIA_BUCKET}" --member "serviceAccount:bharatkatha-${NAME}${SA_SUFFIX}" --role roles/storage.objectUser >/dev/null
    done
    gcloud storage buckets add-iam-policy-binding "gs://${MEDIA_BUCKET}" --member "serviceAccount:bharatkatha-render${SA_SUFFIX}" --role roles/storage.objectUser >/dev/null
    gcloud storage buckets add-iam-policy-binding "gs://${MEDIA_BUCKET}" --member "serviceAccount:bharatkatha-api${SA_SUFFIX}" --role roles/storage.bucketViewer >/dev/null
    for NAME in piper hindi; do
      gcloud storage buckets add-iam-policy-binding "gs://${MODEL_BUCKET}" --member "serviceAccount:bharatkatha-${NAME}${SA_SUFFIX}" --role roles/storage.objectViewer >/dev/null
    done
    ;;
  build)
    # Billable Cloud Build validation. Require SUCCESS for all four builds.
    gcloud builds submit . --project "$PROJECT" --region "$REGION" --timeout=30m --config deploy/main-api/cloudbuild.yaml --substitutions "_IMAGE=${API_IMAGE}"
    gcloud builds submit . --project "$PROJECT" --region "$REGION" --timeout=30m --config deploy/voice-piper/cloudbuild.yaml --substitutions "_IMAGE=${PIPER_IMAGE}"
    gcloud builds submit . --project "$PROJECT" --region "$REGION" --timeout=30m --config deploy/voice-supertonic/cloudbuild.yaml --substitutions "_IMAGE=${HINDI_IMAGE}"
    gcloud builds submit . --project "$PROJECT" --region "$REGION" --timeout=30m --config deploy/render-worker/cloudbuild.yaml --substitutions "_IMAGE=${RENDER_IMAGE}"
    ;;
  deploy)
    : "${FRONTEND_URL:?Exact Vercel HTTPS origin required}"
    : "${MEDIA_BUCKET:?Approved STANDARD Mumbai bucket required}"
    : "${MODEL_BUCKET:?Approved private model bucket required}"
    : "${PIPER_MODEL_PREFIX:?Pinned Telugu model prefix required}"
    : "${HINDI_MODEL_PREFIX:?Pinned Supertonic model prefix required}"
    # Preconditions: migration 002, all four successful builds, secrets, IAM and models.
    # Main API first; private, zero minimum instances.
    gcloud run deploy bharatkatha-api --region "$REGION" --image "$API_IMAGE" \
      --service-account "bharatkatha-api${SA_SUFFIX}" --cpu 1 --memory 1Gi \
      --min-instances 0 --max-instances 2 --cpu-throttling --concurrency 10 \
      --timeout 900 --no-allow-unauthenticated \
      --set-env-vars "APP_ENV=production,GOOGLE_CLOUD_PROJECT=${PROJECT},GOOGLE_CLOUD_REGION=${REGION},GCS_BUCKET=${MEDIA_BUCKET},FRONTEND_URL=${FRONTEND_URL},COOKIE_SECURE=true,COOKIE_SAMESITE=lax,TEXT_PROVIDER=vertex,IMAGE_PROVIDER=worker,IMAGE_WORKER_URL=https://vidbharat-image-worker-3biemw3ouq-el.a.run.app,TTS_PROVIDER=supertonic,ALLOW_IMAGE_FALLBACK=false,PLACEHOLDER_USE_SAMPLES=false" \
      --set-secrets 'DATABASE_URL=bharatkatha-database-url:latest,JWT_SECRET=bharatkatha-jwt-secret:latest,ADMIN_EMAIL=bharatkatha-admin-email:latest,ADMIN_PASSWORD=bharatkatha-admin-password:latest,IMAGE_WORKER_TOKEN=vidbharat-image-worker-token:latest'
    # Private voice workers; English and Hindi share the one Supertonic model.
    gcloud run deploy bharatkatha-piper-te --region "$REGION" --image "$PIPER_IMAGE" \
      --service-account "bharatkatha-piper${SA_SUFFIX}" --cpu 1 --memory 1Gi \
      --min-instances 0 --max-instances 1 --concurrency 1 --timeout 300 --no-allow-unauthenticated \
      --set-env-vars "VOICE_MODEL_BUCKET=${MODEL_BUCKET},VOICE_MODEL_PREFIX=${PIPER_MODEL_PREFIX}"
    gcloud run deploy bharatkatha-hindi-hi --region "$REGION" --image "$HINDI_IMAGE" \
      --service-account "bharatkatha-hindi${SA_SUFFIX}" --cpu 2 --memory 2Gi \
      --min-instances 0 --max-instances 1 --concurrency 1 --timeout 300 --no-allow-unauthenticated \
      --set-env-vars "VOICE_MODEL_BUCKET=${MODEL_BUCKET},VOICE_MODEL_PREFIX=${HINDI_MODEL_PREFIX},SUPERTONIC_HINDI_MODEL_REVISION=aafc6e32416a594460b32413efc49d7fe4ce6d46"
    # Durable scene and render Jobs. No automatic retry charges.
    gcloud run jobs deploy bharatkatha-scenes --region "$REGION" --image "$API_IMAGE" \
      --command python --args cloud_scene_worker.py --service-account "bharatkatha-scenes${SA_SUFFIX}" \
      --cpu 1 --memory 1Gi --tasks 1 --parallelism 1 --max-retries 0 --task-timeout 20m \
      --set-env-vars "APP_ENV=production,GOOGLE_CLOUD_PROJECT=${PROJECT},GOOGLE_CLOUD_REGION=${REGION},GCS_BUCKET=${MEDIA_BUCKET},TEXT_PROVIDER=vertex,IMAGE_PROVIDER=worker,IMAGE_WORKER_URL=https://vidbharat-image-worker-3biemw3ouq-el.a.run.app,ALLOW_IMAGE_FALLBACK=false,ADMIN_EMAIL=unused@example.com,ADMIN_PASSWORD=unused" \
      --set-secrets 'DATABASE_URL=bharatkatha-database-url:latest,JWT_SECRET=bharatkatha-jwt-secret:latest,IMAGE_WORKER_TOKEN=vidbharat-image-worker-token:latest'
    gcloud run jobs deploy bharatkatha-render --region "$REGION" --image "$RENDER_IMAGE" \
      --service-account "bharatkatha-render${SA_SUFFIX}" --cpu 2 --memory 2Gi \
      --tasks 1 --parallelism 1 --max-retries 0 --task-timeout 20m \
      --set-env-vars "APP_ENV=production,GOOGLE_CLOUD_PROJECT=${PROJECT},GOOGLE_CLOUD_REGION=${REGION},GCS_BUCKET=${MEDIA_BUCKET},COOKIE_SECURE=true,ADMIN_EMAIL=unused@example.com,ADMIN_PASSWORD=unused" \
      --set-secrets 'DATABASE_URL=bharatkatha-database-url:latest,JWT_SECRET=bharatkatha-jwt-secret:latest'
    echo 'Private deployment complete; grant scoped IAM, set actual voice URLs and job names, then verify.'
    ;;
  authorize)
    gcloud run services add-iam-policy-binding bharatkatha-piper-te --region "$REGION" --member "serviceAccount:bharatkatha-api${SA_SUFFIX}" --role roles/run.invoker
    gcloud run services add-iam-policy-binding bharatkatha-hindi-hi --region "$REGION" --member "serviceAccount:bharatkatha-api${SA_SUFFIX}" --role roles/run.invoker
    for JOB in bharatkatha-scenes bharatkatha-render; do
      gcloud run jobs add-iam-policy-binding "$JOB" --region "$REGION" --member "serviceAccount:bharatkatha-api${SA_SUFFIX}" --role roles/run.jobsExecutorWithOverrides
    done
    ;;
  configure)
    : "${PIPER_VOICES_JSON:?Set reviewed Telugu Piper manifest JSON}"
    PIPER_URL="$(gcloud run services describe bharatkatha-piper-te --region "$REGION" --format='value(status.url)')"
    HINDI_URL="$(gcloud run services describe bharatkatha-hindi-hi --region "$REGION" --format='value(status.url)')"
    test -n "$PIPER_URL" && test -n "$HINDI_URL"
    gcloud run services update bharatkatha-api --region "$REGION" \
      --update-env-vars "^@^CLOUD_SCENE_JOB=bharatkatha-scenes@CLOUD_RENDER_JOB=bharatkatha-render@SUPERTONIC_HINDI_SERVICE_URL=${HINDI_URL}@SUPERTONIC_HINDI_MODEL_REVISION=aafc6e32416a594460b32413efc49d7fe4ce6d46@PIPER_VOICES_JSON=${PIPER_VOICES_JSON}"
    ;;
  verify)
    # Metadata-only verification. Real video tests must be run separately.
    gcloud builds list --limit=4 --format='table(id,status,createTime)'
    for SERVICE in bharatkatha-api bharatkatha-piper-te bharatkatha-hindi-hi vidbharat-image-worker; do
      gcloud run services describe "$SERVICE" --region "$REGION" --format='yaml(metadata.name,status.url,status.conditions,spec.template.spec.serviceAccountName)'
    done
    for JOB in bharatkatha-scenes bharatkatha-render; do
      gcloud run jobs describe "$JOB" --region "$REGION" --format='yaml(metadata.name,status.conditions,spec.template.spec.serviceAccountName)'
    done
    ;;
  publish)
    # Run only after private health checks and beta login/security review.
    gcloud run services update bharatkatha-api --region "$REGION" \
      --no-invoker-iam-check
    ;;
  rollback)
    # Updates only: restore recorded predecessors. First deployment remains private.
    : "${PREVIOUS_API_REVISION:?Record predecessor API revision}"
    : "${PREVIOUS_PIPER_REVISION:?Record predecessor Piper revision}"
    : "${PREVIOUS_HINDI_REVISION:?Record predecessor Supertonic revision}"
    : "${PREVIOUS_SCENE_IMAGE:?Record predecessor scene image digest}"
    : "${PREVIOUS_RENDER_IMAGE:?Record predecessor render image digest}"
    gcloud run services update-traffic bharatkatha-api --region "$REGION" --to-revisions "${PREVIOUS_API_REVISION}=100"
    gcloud run services update-traffic bharatkatha-piper-te --region "$REGION" --to-revisions "${PREVIOUS_PIPER_REVISION}=100"
    gcloud run services update-traffic bharatkatha-hindi-hi --region "$REGION" --to-revisions "${PREVIOUS_HINDI_REVISION}=100"
    gcloud run jobs update bharatkatha-scenes --region "$REGION" --image "$PREVIOUS_SCENE_IMAGE"
    gcloud run jobs update bharatkatha-render --region "$REGION" --image "$PREVIOUS_RENDER_IMAGE"
    ;;
  *) echo 'Choose prepare, build, deploy, authorize, configure, verify, publish or rollback' >&2; exit 2 ;;
esac
