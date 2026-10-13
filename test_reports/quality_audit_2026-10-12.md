# VidBharat quality audit — 12 October 2026

## Verdict

The current beta is not yet competitive with leading video tools for moving scenes or multilingual speech quality. The verified strength is a guided Indian-language story workflow with creator review and approved images. The present exports animate still images. This audit does not claim a top ranking, native-speaker approval, model fine-tuning, or successful moving-video generation.

## Checks completed

- Backend: 68 tests passed, plus six unittest subtests. This covers native-script routing for all 11 offered languages, font and ASS caption setup, 10 explicit Edge voice routes, Odia's explicit unsupported route, duplicate narration within and across scenes, concept-review gating, stale-review invalidation, image-prompt weather priority, media storage rules, and anonymous API behavior. Five dependency deprecation warnings remain.
- Frontend: production build compiled successfully after the review and message changes.
- Voice service: short audio returned for Hindi, Bengali, Marathi, Telugu, Tamil, Gujarati, Urdu, Kannada, Malayalam, and English. Odia AI voice is not configured. This proves synthesis returned bytes, not pronunciation or dialect quality.
- Existing exports: AYANA is 720 × 1280 at 30 fps for 24.87 seconds; Golden Harvest is 720 × 1280 at 30 fps for 34.97 seconds. Their SRT files have 12 and 17 captions respectively, with no adjacent duplicate caption text or overlapping time intervals.
- Duplicate UI messages: failed scene approval and initial studio load each displayed the same error inline and in a toast. The duplicate toast was removed. Dashboard loading now shows one inline error, so React Strict Mode cannot create two failure toasts from its repeated development mount. A new hard check rejects repeated scene narration, including punctuation-only variants, in all 11 language fixtures.
- Visual continuity: the Golden Harvest sequence shows dry, cracked land and later lush green imagery in a way that confuses the drought timeline. Scene image prompts now carry whole-story context and explicitly prioritize the current scene's weather and action over generic regional scenery. A dry-field regression check passes; new generated images have not been inspected yet.

## Live story samples

| Language | Script | AI review | Voice | Note |
| --- | --- | --- | --- | --- |
| Hindi | Generated, structural checks pass | Provider permission error | Audio returned | Repair appears on screen; needs native review. |
| Bengali | Generated, structural checks pass | Not run after quota error | Audio returned | Needs editorial and native review. |
| Marathi | Blocked by provider 429 | Not run | Audio returned | Historical October 11 test exists, before these changes. |
| Telugu | Live app generated a bicycle-as-plough story | Safety review rejected it | Audio returned | A controlled earlier sample passed, but the latest prompt needs a successful rerun. |
| Tamil | Provider quota prevented live sample | Not run | Audio returned | Offline routing and caption checks pass. |
| Gujarati | Provider quota prevented live sample | Not run | Audio returned | Offline routing and caption checks pass. |
| Urdu | Provider quota prevented live sample | Not run | Audio returned | Offline routing and caption checks pass; prior caption visual check is recorded in BETA_STATUS.md. |
| Kannada | Provider quota prevented live sample | Not run | Audio returned | Offline routing and caption checks pass. |
| Odia | Provider quota prevented live sample | Not run | Unavailable | Recording/upload remains the audio path. |
| Malayalam | Provider quota prevented live sample | Not run | Audio returned | Offline routing and caption checks pass. |
| English | Generated, structural checks pass | Concept and safety review pass | Audio returned | The revised sample shows the valve shut and the repair performed before the result. |

All 11 languages have offline native-script, caption-font, and repeated-line checks. Those checks cannot establish natural phrasing, pronunciation, regional accuracy, or intelligibility. The live Gemini provider returned both HTTP 429 quota and permission errors during the matrix; the evaluator stops on such errors to avoid repeated paid/failed calls. The raw results are in `language_quality_2026-10-12.json` and `voice_quality_2026-10-12.json`.

A single minimal request to the official stable `gemini-3.5-flash` model also returned a quota failure. This points to the configured API project's allowance rather than only the preview model. No further live text retries were made.

## Defects found and changes made

1. Gujarati, Urdu, and Odia bypassed native-script validation; English accepted non-Latin narration. The validator now checks those scripts and rejects empty narration.
2. An unknown region inherited Telangana imagery, and unsupported languages inherited English hook examples. Both defaults now avoid that cultural mismatch.
3. Missing scene directions and identical spoken lines could pass hard checks. They now fail. The final beat requires narration even if labelled `ending`.
4. Review did not compare the script with the creator's original idea. A Concept Editor now checks people, setting, required actions, constraints, and outcome; a failed alignment decision blocks approval. Prompt rules now require on-screen actions before their result and preserve the creator's setting.
5. Scene edits and added/removed scenes left script approval current. They now invalidate it. Rendering requires a current passing review and approval; the scene and render screens link back to review.
6. Duplicate inline/toast errors were removed from scene approval and initial studio load.
7. A Gemini 429 caused rapid fallback calls to other model IDs and could surface a misleading permission error. Text generation now stops on quota/rate limits and returns a specific message; fallback remains for other provider failures.
8. Generic region imagery could contradict a scene's weather and story state. Scene prompts now state the current moment's priority and omit lush landscape cues for dry or damaged settings. A dry-field test covers the prompt, but provider quota blocked a fresh visual sample.

## Competitive bar

Runway offers generated moving-video scenes and character/location references. HeyGen offers multilingual video translation and lip sync. These are useful external bars, not a claim of an identical target customer or independently measured product ranking:

- Runway: https://help.runwayml.com/hc/en-us/articles/37327109429011-Creating-with-Gen-4-Video and https://runwayml.com/product
- HeyGen: https://help.heygen.com/en/articles/11391941-video-translation-languages-we-support

VidBharat has not passed a head-to-head quality study against either product. The immediate product gates are: restore reliable text-provider access; complete live script and review sampling in all 11 languages; obtain native-speaker reviews; measure exact voice duration and pronunciation; pilot true motion on an approved scene; and compare story fit, character continuity, motion, render latency, and cost. No model weights were fine-tuned in this audit.
