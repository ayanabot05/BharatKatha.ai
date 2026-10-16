# Editing journey and release test matrix — 15 October 2026

## Findings fixed

1. Image edits used an instruction for one image call but did not persist the changed concept. Successful edits now save the visual description, synchronize the script and invalidate script approval/export.
2. Whole-story/script/style changes were possible during picture generation. They now return a clear 409 response until generation finishes.
3. Later images retained approval after an earlier concept changed. They now require approval again; a cloud vision continuity review must pass against the updated earlier image before accepting them. Existing image files are preserved, avoiding unnecessary regeneration when they still match.
4. Edits during voice generation could race the eventual voice response. AI voice generation and uploads now hold a per-project lock, released even on errors. Mutating the story or starting export while a voice is being prepared is blocked.
5. Deleting a project during active generation/rendering is blocked.

## Verified this turn

| Area | Evidence | Scope |
| --- | --- | --- |
| Script/content/language/review guards | Full suite: 215 tests passed, 6 subtests | Automated, simulated provider results for workflow faults |
| Midway image concept edit | Saved concept survives reload; earlier approval/export invalidated; unchanged image retained | In-memory workflow simulation |
| Later-scene continuity | Matching picture accepted; changed-character picture rejected | Vision result simulated, not fresh image-quality proof |
| Story changes during generation | Idea/script/style/language/region updates rejected | Five regression cases |
| Voice timing races | Story change rejected; lock released after provider failure | Regression cases; final targeted suite 101 passed |
| Export gates | Stale review/missing audio/missing image/placeholder/unapproved picture rejected | Five regression cases |
| Auth and real database | Seven checks passed in `phase0-real-api-checks.json` | In-process ASGI, actual Supabase, no public hosting |
| Login/logout | Valid account login succeeds; signed-out access rejected | Real credentials used without logging them |
| Missing resources/input bounds | Unknown project/media return 404; excessive page size returns 422 | Does not replace a real two-account isolation test |

## Still unverified — do not call this a complete release test

- Fresh full video generation and rendering using the updated deployed backend.
- Real cloud image edit such as adding a bird, then manually inspecting natural integration and downstream consistency.
- Fresh final narration/caption/image synchronization after those edits.
- Two independent browser accounts against the public deployment.
- Real provider quota outage, server restart during a job, slow mobile network and public Vercel proxy timing.
- All possible topics, languages, user inputs, devices or provider behaviors. A finite test suite cannot cover every situation.

Only the image-worker Cloud Run service exists. The main backend/rendering service is not deployed. Heavy rendering was not moved onto the laptop to bypass the user's cloud-only requirement. Deploy the main backend, then execute the public release checklist in `deploy/PHASE_ZERO.md`. These tests are not a measured 95% content-accuracy result.
