# Product retest — 14 October 2026

## Changes

- Replaced the mobile workflow's horizontal step strip with a dropdown. Applied a cream, white and sage palette to the studio, dashboard, sign-in and growth coach, with compact scene cards and improved text contrast.
- Continued translating common navigation, dashboard, workflow and scene controls when the user selects a language. Remaining copy still needs translation and native review.
- Made the script prompt prioritize concrete content promises over duration. The checklist and semantic audit now check timed actions in the same scene, require whole-script checks for exclusions, and reject visual instructions that explicitly combine multiple moments with “then.”
- Asked image edits to integrate added subjects with matching perspective, light, shadow, depth and occlusion. Images are generated one scene at a time, while creators can proceed to narration.
- Removed the second TTS synthesis pass that previously changed speaking pace to fit a target duration. Render timing now follows measured narration length.

## Verification

- Focused backend content and output integrity suite: **152 passed** after final fixes, with third-party deprecation warnings.
- Frontend tests: **6 passed**; production build passed.
- One real cloud image edit added a sparrow to a saved scene in about **18 seconds**. The bird appeared plausibly perched with matching light and style in visual inspection. See `image_retest_2026-10-14/bird_edit.png`.
- Vertex AI text generation works with ADC on Google Cloud project `ayana-video-studio`.
- Live Telugu script attempts on the same detailed idea exposed reliability problems: one was initially accepted although its time cue and exclusion evidence were invalid; a stronger audit rejected the next draft (47.18 seconds); a stronger prompt produced a draft with the correct time cue but a two-moment image description (38.83 seconds); the final check rejected another draft for unverifiable scene evidence (37.04 seconds). Diagnostics are saved as `script_diagnostic_2026-10-14.json` and `script_retest_2026-10-14*.json`. These samples do not establish a 90% or 95% content rate.
- The local API was restarted and a live Telugu run reached ideas, project creation, script generation, script validation, managed voice preview, and one real scene image. The final image was `ready`, with no placeholder. See `backend/evaluations/beta-te-1791960245.json` and its MP3 companion. Script generation took 18.14 seconds, review 12.98 seconds, and voice preview 3.89 seconds in that run. Other script attempts on the same idea failed with HTTP 502 while the contract or semantic reviewer cited invalid scene evidence; the successful run does not establish reliable generation.
- The successful draft scored **75/100** in the separate story review and was blocked from approval. The reviewer found that a scene showed the leak stopped before the narration finished the repair. The improvement endpoint generated a revised script, but its first reviewer emitted an invalid citation; the draft is now saved with review pending instead of discarded. A fresh review still scored 75/100 because the revised scenes used character commands inside a single-narrator voice-over and showed valve action ahead of narration. The script prompt was tightened for these exact defects, but that final wording has not received a new live quality sample. The frontend tests (**6 passed**) and production build passed after this change.
- A complete approved-story → all scene images → narration → render run was **not** completed. A 90%/95% content-accuracy claim requires a labeled multilingual story set and repeated human review.

## Cloud voice status

- ADC and Vertex text access work. The user rotated the HF token, added an enabled Secret Manager version, and gated Indic Parler model-file access was verified without printing the token.
- The Compute Engine region API reports an `NVIDIA_L4_GPUS` quota of **1** (usage 0) in `asia-south1`. A temporary `g2-standard-4` VM request was rejected because this project is on a free-tier billing account that cannot use non-TPU accelerators. No GPU VM, Indic Parler download, deployment or fine-tuning ran. A private evaluation bucket and least-privilege service account were staged for a future paid-billing run.
- Google Cloud managed Chirp 3 HD voices are accessible in Telugu and nine other app languages. Two short Telugu samples, Kore and Charon, were generated in 2.97 and 1.57 seconds respectively. The user approved both but asked for better pacing and pauses, then approved a separate sample using a short sentence-break pause. The backend now inserts those pauses via Chirp markup and uses Google Cloud voices in the local ignored `.env` and deployment example. The live backend code path returned MP3 audio, and `/api/meta` reported the configured provider. Naturalness has not been formally rated.
- Edge TTS remains a fallback if the cloud provider is not selected. The local ignored `.env` selects Google Cloud Chirp 3 HD. The single-pass change lowers work in code, but no live before/after full-render timing benchmark has been completed.

## Rating

The last demonstrated complete-video rating remains **5/10**. The current evidence is insufficient for a 9.5/10 product rating or 95% script/story precision.

## Later story and full-video retest (14 October)

- Added pre-save content and concept checks, including action order, teaching versus merely demonstrating, visual state before and after repair, timed actions, and concrete scene evidence. The generator can revise a failed draft twice. A malformed reviewer response now gets one retry. These changes favor blocking a doubtful story over approving it.
- An eight-idea automated multilingual benchmark initially passed **2/8**. Follow-up focused reruns remained inconsistent: the latest three-case run passed **1/3**. These are small, overlapping, model-reviewed samples, not a human-labeled accuracy measurement. Hindi school-bag and Ghatotkacha stories still failed or triggered reviewer errors. The 95% target is **not demonstrated**.
- A Tamil kite story passed the live project review at **86/100** after the script showed the grandson applying the patch under Grandma's guidance. The first image batch had patches visible before the repair and inconsistent clothing. Cloud image edits corrected the five-scene sequence; one edit timed out and was retried. The manual corrections show that initial image generation is not yet reliably faithful to story state.
- A complete test project reached real sequential scene images, cloud narration, scene approval, captions, and exported MP4. The final artifact is `complete_flow_case7/final.mp4`. Audio measured **24.76 s** and video **24.72 s**, a **0.04 s** duration difference. Sampled frames at 2, 7, 12, 18 and 22 seconds showed the scene order and burned-in Tamil captions. The managed voice supplies no word timestamps, so caption timing remains **estimated**; precise word-level sync is not verified.
- Final focused backend suite: **166 passed** with only third-party deprecation warnings. The tested video is complete, but a single manually corrected sample cannot establish 95% product-wide accuracy. Current overall product rating is **6/10** pending repeatable multilingual fidelity, automatic image-state consistency, native-language review, and measured caption timing.
