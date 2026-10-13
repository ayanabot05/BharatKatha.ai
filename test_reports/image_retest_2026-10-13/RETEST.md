# Image generation and diagnostic video retest — 13 October 2026

Project: `689d06a42e2b4f86a66fdd4efdae0679` (Telugu, Andhra Pradesh, cartoon).

## Result

- First pass generated scenes 1–2, then the cloud worker returned HTTP 429 for scenes 3–5. The old app marked all three failed and required repeated individual regeneration.
- The updated batch resumed with scenes 1–2 preserved. It generated scenes 3–5 without replacing the finished images. All five scene statuses became `ready`.
- AI narration measured **23.12 s** for a **30 s** request. The diagnostic MP4 measured **23.09 s**. Its video and audio streams decoded without error, and it contains 13 provider-timed caption intervals.
- Captions in the repair close-up sit below the wrench and clamp.
- This is a diagnostic cut assembled from the saved images and narration. The scenes were not approved for publishing in the app.

## Changes made

- Generate only missing scene pictures on batch retry.
- Keep completed images as reference material for later scenes.
- Add a 20-second configurable gap between images, one automatic worker retry after a 30-second cooldown on HTTP 429, and pause the remainder with a clear message if capacity stays unavailable.
- Change the Scene editor action to **Generate missing pictures** and display the paused reason.
- Strengthen story and image prompts for action order and object continuity. Remove the full story summary from individual image prompts because it encouraged later props to appear too early.
- Raise the narration planning floor after the measured shortfall, and move burned-in captions lower.

## Still failing visual acceptance

1. Scene 1 shows a wrench before the inspection/repair action is narrated. These images were generated before the latest prompt change that removes future-story context; that change still needs a fresh image test.
2. Scene 3 shows clamp and wrench work while its narration is still calling attention to rust and escaping water.
3. The younger man gains a moustache and changes sleeves in scene 5.
4. The pipe is consistently rusty and vertical and the final image no longer gushes water, but the cracked metal below the clamp makes the repair outcome visually questionable.
5. The 23.09-second export misses the requested 30 seconds by 6.91 seconds. The new stricter word floor needs a fresh script and voice retest.

Full sequence and video: `scene_1.png` through `scene_5.png`, `diagnostic_retest.mp4`, and `preview.html` in this directory. Live app project is held for review; no image-to-video work has started.

## Narration timing follow-up

The 23.09-second diagnostic video above uses the earlier 43-word script and is unchanged. A fresh 30-second Telugu script generated after the word-count fix contains 57 narration words. Its default voice measured 26.25 seconds; the app's new measured pacing pass adjusted the voice to 0.875× and produced **29.75 seconds**. This verifies timing for the new script and voice, but no new images or video were made for that script. See `../duration_retest_2026-10-13.json`.
