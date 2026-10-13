# Cloud-only language-model experiment

Status: prepared, not submitted or trained. No local fitting is permitted by the entry point.

This experiment trains language-identification weights on WiLI-2018 and adapts them to short excerpts. It does **not** fine-tune Gemini, an image model, or a video model. The application is not configured to use these weights until the resulting evaluation has been reviewed.

Input: original WiLI-2018 archive, fetched inside Cloud Run, verified against the source checksum. Attribution and ODbL licence are recorded by `fetch_wili.py`. The archive, provenance, numerical weights and evaluation are uploaded to a private Cloud Storage prefix. No private OpenAI data or user projects are used.

Execution requirements: authenticated gcloud, Cloud Build and Cloud Run enabled, existing Artifact Registry repository, a private output bucket, and a job service account with object creation permission on that bucket. Use a dedicated training identity; do not grant project-wide storage access. Choose a unique output prefix per execution to prevent overwrites.

Resource envelope: one task, one CPU, 4 GiB RAM, 20-minute timeout, zero retries. Build runs in Cloud Build. No GPU or local Docker build is needed. The envelope bounds job runtime, not the total bill (build and storage also cost money).

Preparation and submission, after the bucket and service identity are verified:

```sh
gcloud builds submit backend/training --tag asia-south1-docker.pkg.dev/ayana-video-studio/vidbharat-beta/language-training:review-v1 --project ayana-video-studio
gcloud run jobs create vidbharat-language-review-v1 --project ayana-video-studio --region asia-south1 --image asia-south1-docker.pkg.dev/ayana-video-studio/vidbharat-beta/language-training:review-v1 --service-account TRAINING_SERVICE_ACCOUNT --cpu 1 --memory 4Gi --tasks 1 --parallelism 1 --max-retries 0 --task-timeout 20m --set-env-vars OUTPUT_GCS_URI=gs://VERIFIED_PRIVATE_BUCKET/UNIQUE_RUN_PREFIX
gcloud run jobs execute vidbharat-language-review-v1 --project ayana-video-studio --region asia-south1
```

The placeholders deliberately prevent submission before cloud resources are inspected. Monitor execution and read `evaluation.json` before deciding whether to integrate. The selected epoch may be zero if adaptation does not improve held-out validation. Test results must not be described as narration or native-speaker certification.
