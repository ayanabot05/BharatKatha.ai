#!/usr/bin/env bash
set -euo pipefail

# Run from an authenticated Cloud Shell after uploading this directory.
PROJECT=ayana-video-studio
REGION=asia-south1
SERVICE=vidbharat-image-worker
REPOSITORY=vidbharat-beta
ACCOUNT=vidbharat-image-worker
SECRET=vidbharat-image-worker-token
IMAGE="${REGION}-docker.pkg.dev/${PROJECT}/${REPOSITORY}/${SERVICE}:beta"

gcloud config set project "$PROJECT"
gcloud services enable aiplatform.googleapis.com run.googleapis.com cloudbuild.googleapis.com \
  artifactregistry.googleapis.com secretmanager.googleapis.com iam.googleapis.com --project "$PROJECT"

if ! gcloud iam service-accounts describe "${ACCOUNT}@${PROJECT}.iam.gserviceaccount.com" \
  --project "$PROJECT" >/dev/null 2>&1; then
  gcloud iam service-accounts create "$ACCOUNT" --display-name="VidBharat image worker" --project "$PROJECT"
fi
SERVICE_IDENTITY="${ACCOUNT}@${PROJECT}.iam.gserviceaccount.com"
gcloud projects add-iam-policy-binding "$PROJECT" --member="serviceAccount:${SERVICE_IDENTITY}" \
  --role="roles/aiplatform.user" --quiet >/dev/null

if ! gcloud artifacts repositories describe "$REPOSITORY" --location "$REGION" \
  --project "$PROJECT" >/dev/null 2>&1; then
  gcloud artifacts repositories create "$REPOSITORY" --repository-format=docker \
    --location "$REGION" --project "$PROJECT"
fi

mkdir -p "$HOME/.config/vidbharat"
chmod 700 "$HOME/.config/vidbharat"
TOKEN_FILE="$HOME/.config/vidbharat/image-worker-token"
if [[ ! -s "$TOKEN_FILE" ]]; then
  python3 -c 'import secrets,sys; sys.stdout.write(secrets.token_urlsafe(48))' > "$TOKEN_FILE"
  chmod 600 "$TOKEN_FILE"
fi
if ! gcloud secrets describe "$SECRET" --project "$PROJECT" >/dev/null 2>&1; then
  gcloud secrets create "$SECRET" --replication-policy=automatic --project "$PROJECT"
fi
gcloud secrets versions add "$SECRET" --data-file="$TOKEN_FILE" --project "$PROJECT" >/dev/null
gcloud secrets add-iam-policy-binding "$SECRET" --member="serviceAccount:${SERVICE_IDENTITY}" \
  --role="roles/secretmanager.secretAccessor" --project "$PROJECT" --quiet >/dev/null

if ! gcloud builds submit . --tag "$IMAGE" --project "$PROJECT"; then
  echo 'Cloud Build was unavailable; building in Cloud Shell with Docker instead.' >&2
  gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet
  docker build -t "$IMAGE" .
  docker push "$IMAGE"
fi
gcloud run deploy "$SERVICE" --image "$IMAGE" --region "$REGION" --project "$PROJECT" \
  --service-account "$SERVICE_IDENTITY" --no-invoker-iam-check \
  --min-instances=0 --max-instances=1 --concurrency=1 --cpu=1 --memory=512Mi \
  --timeout=180 --set-env-vars="GOOGLE_CLOUD_PROJECT=${PROJECT},GOOGLE_CLOUD_LOCATION=global,GEMINI_IMAGE_MODEL=gemini-3.1-flash-image" \
  --set-secrets="WORKER_TOKEN=${SECRET}:latest"

URL=$(gcloud run services describe "$SERVICE" --region "$REGION" --project "$PROJECT" \
  --format='value(status.url)')
printf '\nIMAGE_WORKER_URL=%s\n' "$URL"
printf 'Worker token saved privately at %s\n' "$TOKEN_FILE"
printf 'Put the URL and token in local backend/.env. Do not paste the token in chat.\n'
