# VidBharat localhost end-to-end audit — 13 October 2026

## Verdict and rating

**5/10 as a creator beta; not ready for paid launch.** One fresh Telugu story reached a playable, downloadable MP4 with narration and captions. The exported story is materially wrong: the pipe changes between shots and the final image shows a large leak while the narration says the repair is complete. The 30-second request exported at 21.24 seconds. This rating covers the observed workflow, not a claim about every language, device, or account.

No product code or generated content was corrected during this audit. Frames were approved solely to make a diagnostic export. Image-to-video motion work was not started.

## Live test evidence

- Localhost backend health, existing-account login, idea suggestions, project creation, script generation, and script review returned HTTP 200. The five-scene Telugu script passed the app's review (`all_passed=true`, `safe=true`). See `backend/evaluations/beta-te-1791906136.json`.
- Five real cartoon scene images were generated. Scene 4 was marked `failed` with “Generation was interrupted” on the first attempt, then succeeded on retry. See `fresh_e2e_2026-10-13.json`.
- AI narration and final rendering completed. The MP4 has H.264 video at **720×1280, 30 fps** and AAC mono audio. It is **21.24 seconds** long, although the project requested **30 seconds**. The entire video and audio stream decoded without error. Twelve provider-timed caption intervals were saved.
- The MP4 reloaded from the project and downloaded through the authenticated media endpoint (2,892,730 bytes). Anonymous access returned 401. Thumbnail creation returned 200.
- The metadata endpoint reports 11 creation languages and six styles. A live Telugu/Andhra Pradesh YouTube discovery query returned 200 with zero videos. The Growth Coach returned a measured/hypothesis report and seven-day plan for **synthetic, manually entered** metrics; no account analytics were connected.
- Focused backend verification: 100 pytest checks passed and 20 unittest checks passed. Frontend regression suite: five checks passed. These tests do not validate generated visual truth or native-language pronunciation.

Diagnostic video: `backend/storage/vidbharat/videos/46057842e877488e9a6c7200aa1f29a5/c197561d4a4b409590c7b0c00ab84172.mp4`

Representative exported frames: `fresh_e2e_frames_2026-10-13/scene_1.jpg` through `scene_5.jpg`.

## Issues, ordered by impact

### Output blockers

1. **False story outcome.** Scene 5 narration says the job is finished; its image shows water gushing from an open, disconnected pipe. The app allowed this image to be approved and exported.
2. **Object continuity fails.** Scene 1 has a rusty metal pipe and rope/coupling; scenes 3–5 use a black pipe with a different break and clamp. The same physical joint is not preserved.
3. **Action order and physical action fail.** Scene 1 already shows the men manipulating the leak before the narrated investigation; scene 3 shows a large pipe gap; scene 4 presents an implausible clamp/wrench repair without reconnecting the pipe.
4. **The requested duration is missed.** The 30-second script produced 21.29 seconds of narration and a 21.24-second MP4, about 8.76 seconds short. The UI warns after speech generation but does not produce the selected length.
5. **This is still-image video.** FFmpeg moves the camera over static images. Characters and interacting objects do not animate. There is no demonstrated lip sync.
6. **Output resolution misses the documented HD goal.** Export is 720×1280, rather than the 1080×1920 stated in `plan/plan.md`.
7. **Captions obscure the repair.** The black caption box is readable but covers the pipe and tool at the key action moment in scenes 3–4.
8. **Visual review is not a reliable acceptance gate.** The script review passed before images existed; later approval is manual and did not flag the contradictory final image or changing pipe.

### Workflow and feature gaps against the handwritten goal

9. **Image generation was intermittent.** The fourth scene failed as “Generation was interrupted” and needed a retry in this run. This is one observed failure, not a measured failure rate.
10. **Shot editing is incomplete.** Individual scene text edits, add/delete, and regeneration exist; scene reorder and per-shot timing controls were not found in the studio or project API.
11. **No usable background-music workflow.** The renderer accepts an optional music file, but the render job does not supply one and the Audio Studio has no music selection or volume controls. Its fixed volume mix is not automatic ducking.
12. **The creator does not see a render cost estimate.** No estimate or credit decision was found before “Render my video.”
13. **Fewer visual choices than the goal.** Six styles are exposed. Distinct mythology art and some character concepts in the handwritten goal are not selectable.
14. **Interface localization is partial.** The UI switch offers English, Telugu, Hindi, and Tamil. Many studio headings and instructions remain English even when Telugu is selected; seven other creation languages have no UI option.
15. **Odia has no AI narration route.** Odia captions are offered, but the app requires an uploaded recording for Odia voice.
16. **YouTube/Instagram publishing and analytics are not connected.** The YouTube connect button is disabled; private upload and Instagram integration are not functioning flows. The Growth Coach uses manually entered numbers, not connected analytics.
17. **Live topic discovery was empty for this test query.** The Telugu/Andhra Pradesh village-life search returned no videos. The AI suggestion route did return ideas, but those are labelled as regional suggestions rather than live trends.
18. **Settings describes a different live voice engine.** It claims “OpenAI TTS-HD” under “Live now,” while the API metadata says Edge neural voices are the default and OpenAI TTS is optional.

### Verification still required

19. The signed-in browser walkthrough stopped when Windows Computer Use could not verify the navigation URL. The frontend landing and signed-in Step 1 were visible, but playback controls, mobile layout, accessibility, and all six UI steps were not completed by browser automation. This is a test limitation, not proof of an app defect.
20. Telugu narration pronunciation, idiom, and cultural fit need a native speaker. The audio track decoded, but technical decoding is not editorial approval.
21. The other offered languages need fresh complete-story runs. Prior short voice/caption checks do not establish full-video quality.
22. The in-process duplicate-generation guard has not been proven safe across multiple backend worker processes. No live multi-worker race test was run here.

## Stage assessment

| Handwritten goal | Result |
|---|---|
| Ideas by topic, region and language | AI ideas worked; live discovery returned zero results for this query |
| Script and multi-angle validation | Live script and review worked; review did not protect the final visual story |
| Character/style choice | Six styles; the two men stayed mostly recognizable; the pipe did not |
| Shot-by-shot visual editing | Text edits and regeneration available; reorder/retime not demonstrated |
| Voice, music and audio edit | Voice generated; music controls absent; no fine audio edit tested |
| Captions, export and tags | Captioned MP4 and metadata produced; duration/resolution/visual truth failed |
| Connected growth analysis and guidance | Synthetic manual-metric report worked; account connection absent |
| More views outcome | Not measurable from this test; no view-growth claim is justified |

## Test boundary

This is one fresh, minimally edited story using the app's configured cloud providers and local FFmpeg assembly. No generated frame was repaired before rendering. The completed file proves the pipeline can export a technically valid video; it does **not** prove a publication-ready story. App changes should wait until the user reviews this issue list and preview. After those issues are addressed and retested, evaluate image-to-video generation separately.
