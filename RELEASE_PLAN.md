# VidBharat public beta

## Product commitment

Help first-time creators use their interests and knowledge to make, edit and share
videos in their own language. Ram AI is their personal creation assistant.
Release a broad beta and improve with observed use. Do not label an unavailable
integration as working or promise creator earnings. The claim "India's first"
requires independent market evidence before use in marketing.

## Accepted scope

- Six styles: Human, Cartoon, Cinematic, Emoji, Animals and Storybook.
- Ten launch languages: Hindi, Bengali, Marathi, Telugu, Tamil, Gujarati, Urdu,
  Kannada, Odia and Malayalam. Keep English available as an additional option.
- Translate landing, authentication, dashboard, studio, errors and help. App and
  video languages are separate preferences. Include Urdu right-to-left layouts.
- Voice input, spoken help, script read-aloud and large labelled mobile controls.
- Interests lead to relevant YouTube discovery and original Ram AI suggestions.
- Journey: idea, script, character/style, video scenes, editing, audio, supported
  lip sync, subtitles/thumbnail/publishing text, share/export.
- Back navigation, durable drafts, version history and selective regeneration.
- Later connected analytics feeds weekly/monthly creator guidance.

## Engineering sequence

1. Stabilize state and navigation. Clear stale reviews after script changes,
   surface actionable failures and move long generation work to durable jobs.
2. Build a localization layer and redesign the full mobile journey. Review the
   ten languages with native speakers; a dropdown alone is not language support.
3. Add saved interests and YouTube Data API discovery with source attribution.
   Keep measured data distinct from editorial advice; review API requirements.
4. Save approved character references, appearances and per-scene versions. Feed
   these to image and motion generation rather than relying on a style label.
5. Evaluate short Wan2.2 clips, Indic Parler-TTS, IndicF5, IndicConformer,
   IndicTrans2 and MuseTalk on representative content. Record exact checkpoint
   licences, GPU requirements, latency and cost including unsuccessful attempts.
6. Complete scene editing, narration/music mixing, subtitle timing, thumbnails,
   localized publishing text and export. Enable supported lip sync per style.
7. Add account publishing after provider setup; pilot the complete experience.

## Ram AI improvement

Start with provider-backed generation, clear instructions, structured outputs,
saved creator preferences and editorial review. Do not describe prompt changes
as model training. Collect consented examples of accepted and corrected outputs.
Keep an evaluation set separate from training data. Fine-tune only after baseline
evaluation identifies repeatable failures and a checkpoint licence, training
budget and serving environment are selected. Compare accuracy, language quality,
character consistency and usefulness before adopting the tuned model.

## Cloud execution requirement

The creator's seven-year-old laptop must not run model inference, model training,
lip sync or video rendering. Do not download model weights locally. Use Google
Cloud workers for heavy jobs and a private Google Cloud Storage bucket for source
uploads, character references, audio, previews and final exports. Keep local work
limited to code editing, frontend/backend development and builds (explicitly
allowed by the user). Heavy AI inference/training remains cloud-only. Production
builds can run in cloud CI. Deployment must verify project identity, credit eligibility, GPU quota
and budget before provisioning billable infrastructure.

Use durable queued jobs, per-user object authorization, short-lived signed media
URLs, upload limits, retention rules and explicit worker shutdown/scale-down.
Choose CPU workers for assembly and suitable GPU workers for inference based on
measured requirements. Budget alerts alone do not cap spending; enforce job and
user limits in the application.

## External requirements still unresolved

- Google credits: eligible services, expiry, balance and GPU quota.
- A funded GPU worker or inference service for motion and speech models.
- YouTube API project and account publishing credentials/approval as applicable.
- Voice reference permissions and a commercially licensed music catalogue.
- Native-language reviewers and real first-time creator feedback.

## Initial code changes

Explicit previous-step navigation and an unsaved-change warning for form edits;
recoverable project-load errors; script edits invalidate review/audio/render;
Ram AI prompts localize explanations and distinguish editorial opinions from
measured trends. No model weights have been trained or fine-tuned. This does not
complete localization, motion generation, lip sync or publication.
