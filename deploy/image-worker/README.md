# Vertex image bridge for the local beta

This small Cloud Run service uses its service identity to call Vertex AI. It
generates one real scene image per request and returns the image to the local
backend. It has no GPU, no minimum instances, one maximum instance and one
concurrent request. The service URL is public; a long random token is required
for `/generate`. `/health` exposes no project data.
Cloud Run's Invoker IAM check is disabled for this service so a local backend
without Google Cloud credentials can reach it. The `/generate` token check is
therefore essential; never put the token in frontend code or a public repo.

`deploy.sh` prepares a dedicated service account, Secret Manager token,
Artifact Registry image and Cloud Run service in `ayana-video-studio`. It
creates billable resources and should be run only while the limited beta is
actively being evaluated. This is a bridge for local tests, not the full cloud
deployment or a trained model.
If Cloud Build permission is unavailable, the script builds with Docker in
Cloud Shell and pushes to Artifact Registry instead; this does not use the
laptop CPU.

Upload the `image-worker` directory to authenticated Cloud Shell, enter it,
then run `bash deploy.sh`. The script prints the service URL and stores its
token under `~/.config/vidbharat/image-worker-token` in Cloud Shell. Copy these
values into the local ignored `backend/.env` as `IMAGE_WORKER_URL`,
`IMAGE_WORKER_TOKEN`, and set `IMAGE_PROVIDER=worker`. Do not send the token in
chat. Restart the local backend and generate one scene before running all scenes.

For the first ₹1,000 stage, limit testing to one five-to-seven-scene project and
review the billing page after the first image and before further generations.
Cloud Billing budget alerts are notifications, not a hard spending cap. The
service has zero minimum instances, so it idles when unused. Remove its URL
from the local app after testing; delete the Cloud Run service when this bridge
is no longer needed. Keep the Secret Manager token private.
