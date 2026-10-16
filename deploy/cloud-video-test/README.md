# Fresh cloud video evaluation

This is a single, real-provider Cloud Run Job test. It creates a **new** Telugu
story in the configured Supabase database, reviews it, generates pictures one
at a time, edits the first picture to add a natural sparrow, reviews the changed
story and later pictures, generates managed narration with measured word timing,
and renders a captioned MP4. It never edits an existing creator project.

The job writes a JSON report and three inspection frames under
`gs://$GCS_BUCKET/fresh-video-test-20261015/$CLOUD_RUN_EXECUTION/`. The final
private MP4 URI is recorded in `report.json`. A passing automated report still
requires a human to watch the MP4 and inspect whether the bird, character
continuity, pacing, captions, and scene order look and sound right. It is not a
95% accuracy measurement.

## Cloud prerequisites

- Project `ayana-video-studio`, region `asia-south1`, with Cloud Build, Cloud Run,
  Vertex AI, Speech-to-Text, and Text-to-Speech APIs enabled and billing available.
- A dedicated Cloud Run Job service account with Vertex AI access, permission to
  use cloud speech services, object read/write access to the selected private
  GCS bucket, and Secret Manager access to one Supabase database URL secret.
- An existing test user in that database. The user email is passed as
  `TEST_USER_EMAIL`; the password is neither needed nor passed to the job.
- Secret Manager secret `vidbharat-video-test-db-url` with a current version
  containing only the Supabase `DATABASE_URL`. Do not place the URL in the repo,
  shell command arguments, job logs, or a Cloud Build substitution.
- The database must already have the Phase 0 migration. The job runs a single
  process, keeping in-process image and render tasks alive until completion.

## Build and execute after cloud access is approved

Build from the repository root with the checked-in Cloud Build file:

```powershell
gcloud builds submit . --project=ayana-video-studio --region=asia-south1 --config=deploy/cloud-video-test/cloudbuild.yaml
```

Create a one-task Cloud Run Job using image
`asia-south1-docker.pkg.dev/ayana-video-studio/vidbharat-beta/cloud-video-test:20261015`.
Set `DATABASE_URL=vidbharat-video-test-db-url:latest` through Cloud Run's
**secret reference**, not a plain environment value. Set plain environment
values `TEST_USER_EMAIL` and `GCS_BUCKET`. Use the dedicated service account,
2 CPU, 4 GiB memory, a 3600-second task timeout, and **zero retries** so a
provider error cannot automatically create another billed evaluation project.
Execute it once with `gcloud run jobs execute ... --wait`.

If the job fails, read its `report.json` and Cloud Logging stage marker before
retrying. A failed review, image audit, quota, voice alignment, or render is a
real failed test; the harness does not force approval or substitute placeholders.

The main backend and Vercel frontend are separate deployment gates. This job
tests the media pipeline in Google Cloud; it does not prove a public browser
journey works.
