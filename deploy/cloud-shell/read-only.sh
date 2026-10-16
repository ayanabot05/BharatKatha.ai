#!/usr/bin/env bash
set -euo pipefail
PROJECT=ayana-video-studio
REGION=asia-south1
gcloud config set project "$PROJECT" >/dev/null
gcloud auth list --filter='status:ACTIVE' --format='table(account,status)'
gcloud beta billing projects describe "$PROJECT" --format='yaml(billingEnabled,billingAccountName)'
gcloud run services list --region "$REGION" --format='table(metadata.name,status.url)'
gcloud run jobs list --region "$REGION" --format='table(metadata.name)'
gcloud artifacts repositories list --location "$REGION" --format='table(name,format)'
gcloud storage buckets list --project "$PROJECT" --format='table(name,location,storageClass)'
gcloud services list --enabled --filter='NAME:(run.googleapis.com OR cloudbuild.googleapis.com OR artifactregistry.googleapis.com OR storage.googleapis.com OR secretmanager.googleapis.com OR cloudtasks.googleapis.com)' --format='table(NAME)'
gcloud iam service-accounts list --format='table(email)'
gcloud secrets list --format='table(name)'
gcloud run services describe vidbharat-image-worker --region "$REGION" --format='yaml(metadata.name,status.url,spec.template.spec.serviceAccountName,spec.template.spec.containers.resources)'
