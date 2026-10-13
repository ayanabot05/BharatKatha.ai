# Limited beta status — 11 October 2026

## Independent review checkpoint — 13 October 2026

- Latest evidence: `test_reports/independent_review/AUDIT_2026-10-13.md`. Backend: 113 tests plus six subtests passed. Frontend: five targeted regression tests passed. Twenty real short voice samples across ten languages passed decode/timing checks; captions rendered in all eleven offered languages. These results are not native-speaker approval.
- Strengthened review fingerprints, scene-level script checks, exact concept citations, measured speech caption timing, recording transcription requirements, bundled caption fonts and voice-preview cleanup. Opening/ending edits now change actual scene narration.
- Correction to the older entry below: the cloud image worker is available. A new image and its refinement were generated, but the physical pipe-repair action still fails visual inspection. The saved text probe hit quota. True generated motion remains absent.
- Training must run on Google Cloud, per the creator. A bounded Cloud Run language-classifier experiment is prepared, but authenticated gcloud access is pending. No model weights have been trained; no generative-model fine-tuning or competitive-leadership claim is justified.

## Quality and all-language audit — 12 October 2026

- `test_reports/quality_audit_2026-10-12.md` records the current evidence and gaps. The backend suite passed 68 tests plus six unittest subtests, and the frontend production build passed. Short Edge audio returned for 10 offered languages; Odia AI voice is unavailable. Offline native-script, ASS caption-font and repeated-line checks cover all 11 languages. This is not native-speaker quality approval.
- A live Telugu app flow generated an implausible bicycle-as-plough story; the safety reviewer rejected it and script approval returned HTTP 400. A controlled English story passed the revised review and showed the repair on screen. Hindi and Bengali scripts passed structural checks, but subsequent review/generation calls hit Gemini HTTP 429 quota or permission errors. The full live language matrix remains incomplete.
- Added a creator-idea Concept Editor to the script review, hard checks for missing and repeated scene narration, and approval/render gates that require a current passing review. Changing, adding or removing scene content now invalidates the old approval. Duplicate inline/toast errors were removed from scene approval and initial studio load; dashboard loading now uses one inline error to avoid duplicate failure toasts under React Strict Mode.
- Gemini text calls now stop on HTTP 429 instead of rapidly trying every fallback model and potentially turning a quota failure into a misleading permission error.
- One minimal call to stable `gemini-3.5-flash` also hit a quota failure. The remaining live language reviews were not retried after that result.
- The two saved MP4s and SRT files were inspected for dimensions, duration, adjacent duplicate captions and overlapping caption times. No adjacent duplicates or overlaps were found. Golden Harvest remains 34.97 seconds against a 30-second target, and its dry-to-lush scene imagery confuses the drought timeline. Image prompts now favor the current scene's weather and action over generic regional scenery; a regression test passes, but fresh images are blocked by provider access. Both videos use camera motion on still images, not generated moving scenes. No model weights were trained or fine-tuned.

## Voice choices and current AYANA render — 12 October 2026

- The default Edge TTS path has only two distinct voices per language. The six named options in Audio Studio mapped three each to the same female or male voice. The UI and API metadata now expose two honest choices, and the missing local `edge-tts` dependency was added to `backend/requirements.txt` and installed in the existing `venv`. A short English synthesis returned audio; the frontend production build passed.
- The creator's `Staying Connected with Ayana` project has six real pictures and audio, but scenes 1 and 2 are not approved. Its render status is `idle`; no MP4 has been made for that project. The render page now lists the exact incomplete scenes and links to the Scene editor. The creator must inspect and approve those pictures before rendering.
- A later database check showed scene 1 approved and scene 2 still unapproved, confirming at least one approval click reached the API. The Scene editor now shows an Approving state or an inline error and prevents overlapping approval requests. Frontend build passed. Scene 2 and the final render remain pending creator action.

## AYANA comparison and scene navigation — 12 October 2026

- A separate AYANA comparison project used the app flow: edited script, Ram AI review (85, safe, all hard checks passed), Human AI style, five real Vertex scene pictures, individual approvals, Edge narration and FFmpeg export. The 24.87-second 720 × 1280 H.264/AAC render with burned English captions, cover and exact storyboard are in `deliverables/ayana-promo/`. A final branded cut adds an end card; the untouched app render is retained for comparison. These are animated still pictures, not true generated moving scenes or lip sync.
- Fixed the project update path so saving a script and style together preserves the new script's scene narration. Narrowed image prompts to characters named in the current scene; the five AYANA images were reviewed for story and character fit before approval.
- The scene editor now allows Continue to voice when each scene has narration and visual directions, even while picture generation or approval is pending. Export still requires approved real pictures. The interface displays the outstanding picture states, missing text explanation and any navigation request error. Frontend build passed after the change.
- The user's existing project was not modified during comparison. Its precise disabled-button state was not accessible from the separate test account. Local frontend and backend were restarted on ports 3003 and 8000.

## Current result — 11 October 2026, after cloud image integration

- The creator supplied the worker token privately in the ignored `backend/.env`. The restarted local backend used the Cloud Run worker in `ayana-video-studio` to generate five **real** 9:16 storybook scene images for the existing Telugu test project `9e63c2127d374ef1812376586ebab39a`. Every image was visually reviewed for the same farmer, attire, setting and story sequence, then approved. The first scene's old sample placeholder was replaced.
- The app rendered a 34.97-second 720 × 1280 H.264/AAC MP4 with Telugu narration and burned captions. Timeline frames at 2, 8, 15, 22 and 30 seconds were reviewed; the captions were legible and the intended scene order was present. The video, thumbnail, SRT and publishing copy are in `deliverables/golden-harvest/`. This output animates approved still pictures with camera motion; it is **not** generative moving-scene video or lip sync.
- The image worker returned HTTP 200 for authenticated scene jobs; unauthenticated generation returned 401. The cloud trial balance was last reported by the creator before these five image calls, so the actual billed cost must be read from Cloud Billing. No GPU training or model-weight fine-tuning was performed. The requested 30-second target became 35 seconds of narration; duration control and native-speaker voice review remain open quality issues.
- The deployed worker image predates the local explicit 9:16 image-config update. The five real images nevertheless came back vertical. A future Cloud Run rebuild can pick up the explicit config; it was not needed for this deliverable.

The entries below record earlier stages and blockers that were subsequently resolved.

## Latest creator review and blocking issue

- The creator's exported 24.9-second MP4 used sample scene pictures unrelated to the approved Krishna story. The renderer applied Ken Burns motion to still images; it did not generate moving video scenes.
- Disabled `ALLOW_IMAGE_FALLBACK` and `PLACEHOLDER_USE_SAMPLES` in the ignored local backend environment. Placeholder pictures are now always rejected by the render endpoint. Each real scene picture must be inspected and explicitly approved before voice/export; regeneration or visual edits revoke approval. Existing exports are not evidence of visual correctness.
- Starting a new script or revision now clears the prior render. Script/style changes and image regeneration are blocked during an active render to prevent an old MP4 from being attached to a new story.
- A fresh Gemini Developer API image call returned 429 with zero free-tier image quota. The creator enabled `aiplatform.googleapis.com` in `ayana-video-studio`, but a repeat Vertex AI probe using the existing API key still returned 403 (blocked API method). Authenticated Cloud Shell requests succeeded with HTTP 200 for both Vertex `gemini-2.5-flash` text and `gemini-3.1-flash-image`; the image response contained image data. This establishes project access, not visual quality or integration. The local app has no ADC, so enabling the API alone cannot make local image generation work.
- The YouTube API key is configured in the ignored local environment. Recent, short YouTube results now use the chosen language and story category, with region/audience relevance clues and six-hour caching; the creator confirmed Telugu moral-story results in the UI. This is not a state-level trending ranking.
- The local page on port 3003 and API health endpoint on port 8000 both returned HTTP 200 after restart. This establishes availability, not a completed real-image video.
- Added a token-protected Cloud Run image bridge and a dedicated service-account deployment script. A local route check returned 200 for health and 401 without the token. The source is packaged in `deploy/vidbharat-image-worker.zip` for Cloud Shell upload; it has not yet been deployed or connected to the local app. The full video flow still needs real scene and editorial review.
- The creator uploaded the worker archive to Cloud Shell. Setup created the dedicated service account, Artifact Registry repository and Secret Manager token. An initial `gcloud builds submit` failed with `PERMISSION_DENIED`; the creator granted `roles/cloudbuild.builds.builder` to the Compute default service account and reran the build successfully. The pushed image digest is `sha256:dd9fec073104866262fe9ce6c3d41f94d7fb5ed4e7df6040d5ada88d0dfefae0`. The uploaded worker source preceded the local 9:16 image-config update, so a later rebuild will be needed to deploy that exact update.
- Cloud Run deployed revision `vidbharat-image-worker-00001-jsp`, but its automatic `allUsers` IAM policy step failed. Both service URLs returned HTTP 403 on `/health`, so the local app cannot invoke the worker yet. The creator is applying Google's `--no-invoker-iam-check` option; `/generate` continues to require the separate Secret Manager token.
- The creator applied `--no-invoker-iam-check`. The canonical Cloud Run URL returned HTTP 200 for `/health` and HTTP 401 for a `/generate` POST without the worker token. Local `backend/.env` now selects `IMAGE_PROVIDER=worker` and the service URL; the private token is awaiting entry by the creator. No authenticated image request through the app has succeeded yet.

## 11 October progress

- Reworked the public landing page again after design feedback. The original Telugu short demo is back inside the hero phone. The six-face CSS 3D carousel now replaces the flat grid in the six-style section, with automatic rotation, manual controls, responsive depth, and reduced-motion support. The page uses a warm cream, charcoal, and muted rose palette; it no longer advertises unimplemented payment plans. This is a frontend build-verified change, not a browser screenshot-verified design review.
- Tuned Ram AI's idea and script prompts for distinct, grounded concepts, simpler spoken language, scene continuity, shorter hooks, and duration-aware narration budgets. Added a text-length check to flag likely overlong scripts before voice generation. These are prompt/rule changes, **not** trained or fine-tuned model weights; generated audio remains the timing source of truth.
- A new live run using the same test account passed login, six ideas, five-scene script generation, review, approval, and scene edit/add/remove. The generated project's English title was `Four Borewells and a Leaf's Miracle`. This run did not generate audio or imagery, so it does not establish actual voice duration or video quality. The full frontend build passed after moving the 3D gallery.
- Editorial inspection of that Telugu story found an implausible leaf-based water-finding method and an automatic "like and subscribe" ending despite passing the existing craft checks. Prompts and reviewer instructions now reject unsupported practical farming techniques and default engagement requests. A second saved Telugu draft used a plausible Anantapur farmer, lower-water crop choice, and drip irrigation, with 34 narration words for the 30-second target; it has not yet passed a live review or audio timing check. The evaluation helper now prints native text on Windows without crashing.

- Reused one dedicated test account (`vidbharat-beta-e2de37b42d@example.org`; credentials stay in ignored `backend/evaluations/test_account.json`). A live authenticated run produced six ideas, a five-scene Telugu script, review, approval, storybook selection, and successful add/edit/remove scene responses. The generated story was titled `రైతు పండించిన నిజమైన బంగారం`. Its narration ran 35.11 seconds against a requested 30 seconds, so duration control still needs improvement.
- Real image requests returned HTTP 429 with `generate_content_free_tier_requests` limit zero. Earlier local runs used labelled sample placeholders; that fallback is now disabled and cannot be exported.
- AI narration succeeded through Edge TTS. The configured OpenAI voice key returned HTTP 401; Edge is now the default to avoid unnecessary failed paid-provider requests.
- Added scene narration/visual editing, add/remove controls, stale asset invalidation, vertical thumbnail creation from real scenes, and native file sharing where supported. The thumbnail endpoint rejects placeholders.
- Added ten requested Indian languages to the idea picker and text/voice routing. Free Edge voices were verified for nine; Edge has no Odia voice. Odia AI voice awaits a cloud worker such as [Indic Parler TTS](https://huggingface.co/ai4bharat/indic-parler-tts), while recording and upload remain available. The full interface is still in English and therefore does not yet meet the low-literacy localization goal.
- Bundled open-licensed Noto fonts and moved burned captions and thumbnail text to FFmpeg/libass. Urdu joining was checked visually in a rendered frame and cover. Other languages still need native-speaker visual review.
- Added read-only YouTube discovery through the official Data API. A key is now configured in the ignored local backend environment. The creator confirmed language/category-relevant results; these are recent search results, not a state-level popularity ranking.
- Frontend production build passed. Six isolated backend tests passed. The full HTTP suite initially had 25 passes and two failures caused by its assumption that the admin already owns a completed video; those two fixture-dependent checks now skip when no completed video exists. The follow-up API and backend run had 23 passes, two skips and two live-AI tests intentionally deselected.
- The landing page received a light, high-contrast layout. Its six style images now use a responsive grid with labels below the images instead of a clipped, fading marquee. Hero text, navigation, feature cards, pricing cards and small-screen spacing were revised from the user-provided screenshots. Scene cards now use one column on phones. The frontend rebuilt and both local services returned HTTP 200. Browser screenshot verification remains unavailable under the local URL policy.
- Local frontend and backend were started on ports 3003 and 8000. Browser visual automation remained unavailable under its local URL policy, so the UI was not visually verified in a browser.
- No cloud training, GPU inference, lip sync, deployment, or spending occurred. The user confirmed an authenticated Cloud Shell for project `ayana-video-studio`, an active Free Trial balance of about ₹28,797, expiry on 8 January 2027, and billing enabled. `GPUS_ALL_REGIONS` is 0. In `asia-south1`, regional on-demand and preemptible T4 and L4 quotas are each 1 and unused, while A100 quotas are 0. Both global and regional quota must allow a GPU, and Google Cloud's Free Trial terms also prohibit adding VM GPUs or requesting quota increases. Upgrading to paid billing is a separate financial decision; no upgrade has been made. Image quota resolution and reviewed training examples are still needed.

## Verified locally

- Frontend development server compiled successfully on port 3003.
- Latest frontend production build completed successfully.
- Backend started successfully on port 8000 with configured database access.
- Health, login and authenticated session returned HTTP 200.
- All 15 backend regression tests passed.
- Telugu live evaluation: ideas, a five-scene script, localized review and audio
  returned HTTP 200. Title: నీటి బంధం.
- Marathi live evaluation: ideas, a five-scene script, localized review and audio
  returned HTTP 200. Title: नात्यांची जोडणी.

These results establish working requests and structured output, not native-speaker
approval, voice quality, visual character consistency or a successful final render.
The Marathi baseline voice preview did not pass its explicit language; this was
fixed subsequently and needs another native-speaker audio check.

## Observed failures

- Gemini image generation returned a 429 with free-tier request quota limit zero.
  The resulting scene was a labelled developer placeholder, not a generated image.
  The original evaluation report's generic completed status must not be read as
  image success. The evaluator now explicitly fails this case.
- OpenAI speech returned 401. The existing Edge TTS fallback produced the audio.
  Provider credentials themselves were not changed.
- A second Telugu evaluation stalled during script review and timed out after
  180 seconds. It did not reach the improvement step. A 60-second text-call
  timeout with an actionable error is now implemented and regression-tested;
  another successful live review/improvement cycle is still needed.
- Browser automation rejected the local page under its URL policy. No visual
  browser QA was completed or bypass attempted.

## Fixes and preparation

- Session refresh now includes initial /auth/me calls.
- Voice preview explicitly passes the project language (important for Marathi).
- Scene cards identify placeholder images.
- Safety reviews reject malformed output and string booleans; no fabricated
  default passing score is assigned to invalid output.
- Hook length is labelled as a text estimate, not measured three-second pacing.
- New AI audio timings no longer include unrecorded quarter-second gaps.
- Subtitle text is also saved inside the render JSON supported by the Supabase
  adapter, and frontend subtitle URLs are released when no longer needed.
- Optional private GCS storage uses the worker's service account. Mocked upload
  tests passed; no live bucket connection has been tested.
- Docker, Cloud Build, HTTPS/Compose and closed-registration beta configuration
  prepared. Docker and gcloud were not available on the local command path;
  the container image itself has not been built or deployed.
- Dataset preparation accepts reviewed, permitted examples and rejects exact
  duplicate prompts. No training dataset or fine-tuned model has been created.

## Decisions needed before cloud training/deployment

The first ₹1,000 gross cloud-use stage is authorized. Confirm the billing-account
type and any per-service spend caps before paid inference. Resolve image quota,
connect private storage, and prepare reviewed training examples and held-out
evaluations. GPU workers require a separate paid-billing upgrade and subsequent
regional and global GPU quota approval. Cloud Shell is open, but the project has
not been changed and no cloud resources have been provisioned.
Training must precede deployment as requested. Do not provision training or
hosting merely because the configuration files exist.

The full ten-language interface, moving-video generation, lip sync, thumbnails,
direct publishing, durable jobs and per-user cost limits remain future work.
