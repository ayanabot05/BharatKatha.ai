# Fresh cloud video test — 15 October 2026

## Current result

**No fresh cloud video has been produced.** The media pipeline has not passed
this test. The only deployed Cloud Run service is the image worker; the main
backend/render service is not deployed.

## Prepared

- Added `backend/cloud_video_test.py` and a minimal Cloud Build image under
  `deploy/cloud-video-test/`. The runner executes only inside a Cloud Run Job.
- It creates a fresh Telugu story, runs the script review, generates scene
  images sequentially, makes a natural bird edit, reviews later images, checks
  word-timed captions, renders an MP4, and compares voice/video duration.
- Failures keep approvals blocked. It does not use sample or placeholder images.
- It records the private video URI, the review results, duration checks, and
  three frames in a GCS JSON report for subsequent human review.
- `python -m py_compile backend/cloud_video_test.py` and `git diff --check`
  passed.

## Execution blockers

1. Cloud creation of the temporary test service account and Secret Manager
   secret was not executed. Automatic approval review reported a usage limit
   and could not review that cloud mutation. This was a review failure, not a
   finding that the action was unsafe. No alternate route was used.
2. The focused local workflow rerun could not start its first async test in
   the current Windows sandbox. `faulthandler` showed Python stuck creating
   `asyncio`'s local socket pair (`socket.accept` in
   `_fallback_socketpair`). This is an environment limit, not a test pass or
   an application failure. The earlier 215 passing workflow tests are recorded
   in `EDIT_JOURNEY_2026-10-15.md`.

## Remaining work

After cloud mutation review is available, provision the isolated job identity,
database URL secret reference, and private GCS permissions; build and execute
the job once in `ayana-video-studio` / `asia-south1`. Inspect `report.json`,
watch the private MP4, and score story accuracy, visual continuity, bird
integration, voice pacing, caption timing, and total wait time. Then run the
public browser journey after the main API and Vercel frontend are deployed.
