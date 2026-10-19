# Phase 3 - Final Motion Quality Validation

**Directive:** produce three short 2.5D MP4 samples with the validated, optimized
engine and decide whether the motion is convincing enough for real YouTube
Shorts creators.

**Scope:** local CPU only. No production code, schema, frontend or cloud
change; no deploy, push, paid API, GPU or extra model download. Everything is
inside `experiments/depth_parallax/`. Phase-1 and Phase-2 artifacts are intact.

**Bottom line:** `CONDITIONAL GO` - the motion is smooth, artifact-free and
cheap on CPU, but **the founder must watch the three side-by-side videos and
sign off** before any production integration (section 7).

---

## 1. Scenes and outputs

Three diverse scenes, taken from the Phase 2 set, from three different projects:

| Key | Role | Phase 2 id | Source image |
|---|---|---|---|
| `char` | Human character (face close-up + hands) | S04 | `backend/storage/vidbharat/scenes/46057842.../04a2a7c2217e406a884d9d1540f1f693.png` |
| `village` | Indian village / landscape (full-body, walking) | S08 | `backend/storage/vidbharat/scenes/aafb7493.../2cd86277eeeb4f24a6c75ea3ed831c0c.png` |
| `complex` | Complex environment (group under banyan tree) | S14 | `test_reports/handover_dry_run/scene_4.png` |

All outputs are in **`experiments/depth_parallax/out/phase3/`**:

**2.5D motion samples (optimized `ParallaxScene`)**

| File | Size |
|---|---|
| `char_2p5d.mp4` | 1.04 MB |
| `village_2p5d.mp4` | 1.89 MB |
| `complex_2p5d.mp4` | 1.96 MB |

**Ken Burns comparisons (existing production engine, same source + duration)**

| File | Size |
|---|---|
| `char_kenburns.mp4` | 0.52 MB |
| `village_kenburns.mp4` | 0.83 MB |
| `complex_kenburns.mp4` | 0.75 MB |

**Labelled side-by-side comparisons**

| File | Size |
|---|---|
| `char_sidebyside.mp4` | 1.52 MB |
| `village_sidebyside.mp4` | 2.55 MB |
| `complex_sidebyside.mp4` | 2.54 MB |

Supporting stills: `<key>_depth.png`, `<key>_2p5d_frames.png` (10 frames across
the clip), `<key>_keyframes_compare.png` (begin/mid/end, Ken Burns vs 2.5D).

Settings: 720x1280, 30 fps, H.264 (libx264, CRF 20, yuv420p), 7.0 s, 210
frames, conservative amplitude with adaptive strength (see section 4).

---

## 2. Verification (FFprobe-equivalent) - all nine files

> Note: the `ffprobe` binary is **not** bundled with `imageio-ffmpeg`
> (it ships `ffmpeg` only) and I deliberately did not download additional
> binaries. Metadata and a full-decode check were therefore done with the
> bundled **FFmpeg 7.1** (`ffmpeg -i` + `ffmpeg -f null -`), cross-checked with
> OpenCV frame counts. Raw output: `out/phase3/ffmpeg_probe_report.json`.

| File | Codec | Resolution | FPS | Duration | Frames | Decodes cleanly |
|---|---|---|---|---|---|---|
| `char_2p5d.mp4` | h264 | 720x1280 | 30.0 | 7.00 s | 210 | yes |
| `char_kenburns.mp4` | h264 | 720x1280 | 30.0 | 7.00 s | 210 | yes |
| `char_sidebyside.mp4` | h264 | 1440x1280 | 30.0 | 7.00 s | 210 | yes |
| `village_2p5d.mp4` | h264 | 720x1280 | 30.0 | 7.00 s | 210 | yes |
| `village_kenburns.mp4` | h264 | 720x1280 | 30.0 | 7.00 s | 210 | yes |
| `village_sidebyside.mp4` | h264 | 1440x1280 | 30.0 | 7.00 s | 210 | yes |
| `complex_2p5d.mp4` | h264 | 720x1280 | 30.0 | 7.00 s | 210 | yes |
| `complex_kenburns.mp4` | h264 | 720x1280 | 30.0 | 7.00 s | 210 | yes |
| `complex_sidebyside.mp4` | h264 | 1440x1280 | 30.0 | 7.00 s | 210 | yes |

Similarly to Phase 2, the benchmarks below separate **objective measurements**
from my **subjective visual judgement**.

---

## 3. Temporal quality assessment

### Objective measurements (`out/phase3/temporal_metrics.json`)

| Clip | f2f MAE mean | f2f MAE max | jump ratio (max/mean) | jerk mean | border min px | global shift mean |
|---|---|---|---|---|---|---|
| `char_2p5d` | 0.72 | 1.17 | 1.62 | **0.10** | 0 (source content) | 0.011 |
| `village_2p5d` | 1.33 | 2.08 | 1.56 | **0.09** | 0 (source content) | 0.027 |
| `complex_2p5d` | 1.28 | 1.96 | 1.53 | **0.09** | 0 (source content) | 0.015 |
| `char_kenburns` | 2.90 | 4.96 | 1.71 | 0.79 | 0 | 0.221 |
| `village_kenburns` | 6.00 | 9.32 | 1.55 | 1.90 | 0 | 0.212 |
| `complex_kenburns` | 5.89 | 10.16 | 1.73 | 2.31 | 0 | 0.203 |

Reading these:

* **No sudden jumps.** `jump ratio` (largest single frame-to-frame change vs the
  average) is 1.53-1.62 - the usual rise/fall of a smoothstep ease, not a spike.
  A real jump would push this well above ~3.
* **No flicker.** `jerk` (mean second difference) is 0.09-0.10 for 2.5D - an
  order of magnitude below Ken Burns (0.79-2.31). Inter-frame change is nearly
  constant. A structural reason backs this up: **depth is estimated once per
  scene, not per frame**, so there is no temporal depth jitter to flicker.
* **No black borders / missing pixels.** `border_min_pixel = 0` is **source
  content**: the base images themselves contain pure-black pixels
  (`base_min = 0`), and the renderer reproduces the border exactly
  (frame border min == base border min, e.g. `village` t=0 / t=1 = 0). No new
  black or missing pixels are introduced. The radial edge feather keeps the
  remap inside the image (`out_of_bounds = 0`, Phase 2).
* **Global motion is monotonic and steady.** Sub-pixel global translation with
  tiny per-frame change (dx std 0.003-0.004).

### Subjective visual judgement (begin / middle / end + 10 intermediate frames)

Inspected `char_2p5d_frames.png`, `village_2p5d_frames.png`,
`complex_2p5d_frames.png` and `<key>_keyframes_compare.png` directly:

| Check | Result |
|---|---|
| Temporal flicker | none seen |
| Jitter / sudden jumps | none seen |
| Face deformation | **none** - the `char` face and `complex` standing figure stay intact across all frames |
| Background tearing | none - tree/pillar/crowd boundaries hold |
| Edge halos | none |
| Unnatural movement | none, though the camera energy is *gentle* (see below) |
| Black borders / missing pixels | none |
| Smooth camera movement | yes - smooth push-in with a slow lateral sweep |

### One honest observation: the 2.5D clips are *gentler* than the Ken Burns hook

The 2.5D preset uses a **9 % push-in** plus a small lateral sweep, whereas the
production hook (scene beat 0) pushes in **18 %**. Consequently the 2.5D clips
change less per frame (f2f MAE 0.7-1.3) than Ken Burns (2.9-6.0). The parallax
is clearly present - background moves relative to the subject - but the overall
camera energy is roughly half. It is not a defect, but a tuning choice: matching
the hook's energy would mean raising `zoom` to ~0.16-0.18 (and/or the lateral
amplitude). I kept it conservative, as instructed, and flag it as a decision.

---

## 4. Performance (local CPU, `DAP_THREADS=2`)

| | 2.5D (optimized) | Ken Burns (production) |
|---|---|---|
| `char` wall time | 7.87 s | 2.62 s |
| `village` wall time | 8.25 s | 2.61 s |
| `complex` wall time | 7.54 s | 2.66 s |
| Frame generation | 33.7-36.8 ms/frame | (inside FFmpeg zoompan) |
| Peak RAM (per clip) | 124-127 MB | 105-112 MB |
| Python CPU usage | ~115 % (≈1.15 cores of 2) | n/a (FFmpeg subprocess) |
| Placement of depth + render | one streaming pass | n/a |

* Adaptive strength used: `char` 1.00, `village` 0.98, `complex` 1.00
  (`adaptive_strength` on the cached depth map).
* Depth maps were served from the Phase-2 cache (`out/depth_cache/*.npy`), so
  no depth inference ran this round; a cold project pays ~2-3 s/scene extra.
* **2.5D is ~3x the wall time of Ken Burns** for the same clip. Scaled up, a
  ~45 s Short (≈6-7 scenes) is ~50 s of frame generation with 2.5D vs ~17 s
  with Ken Burns - still **under a minute, local, CPU-only, ₹0**.

---

## 5. Updated automated tests

```
backend\venv\Scripts\python.exe -m pytest experiments\depth_parallax\tests -q
22 passed
```

Three motion-quality tests were added this round:

* `test_parallax_scene_motion_is_temporally_smooth` - frame-to-frame change is
  steady (no jump beyond 4x the median) while still moving.
* `test_parallax_scene_has_no_black_border` - no black/missing pixels at the
  frame border under strong displacement.
* `test_parallax_scene_render_video_writes_mp4` - the streaming H.264 writer
  produces a playable file and leaves no temp files.

Combined with the Phase 1/2 tests (polarity, genuine-parallax, out-of-bounds,
adaptive strength, optimized-vs-accurate agreement), the geometry is proven
correct and bounded. **These tests do not, and cannot, prove that the motion
*looks* good** - that is why the founder must watch the videos.

---

## 6. Exact output paths

```
experiments/depth_parallax/out/phase3/
  char_2p5d.mp4              char_kenburns.mp4        char_sidebyside.mp4
  village_2p5d.mp4           village_kenburns.mp4     village_sidebyside.mp4
  complex_2p5d.mp4           complex_kenburns.mp4     complex_sidebyside.mp4
  char_depth.png             village_depth.png        complex_depth.png
  char_2p5d_frames.png       village_2p5d_frames.png  complex_2p5d_frames.png
  char_keyframes_compare.png village_keyframes_compare.png complex_keyframes_compare.png
  motion_benchmark.json      temporal_metrics.json    ffmpeg_probe_report.json
```

Reproduce:

```powershell
$env:DAP_THREADS="2"
backend\venv\Scripts\python.exe experiments\depth_parallax\render_motion.py
backend\venv\Scripts\python.exe experiments\depth_parallax\temporal_check.py
```

---

## 7. Final recommendation: CONDITIONAL GO

| Gate | Requirement | Result |
|---|---|---|
| Real 6-8 s / 720x1280 / 30 fps / H.264 samples | yes | **3 produced, all verified** |
| Ken Burns comparisons | yes | **3 produced** |
| Side-by-side comparisons | yes | **3 produced** |
| No flicker / jitter / tearing / halos / black bars | required | **none detected (metrics + visual)** |
| Face / structure preservation | required | **preserved in all three** |
| Practically cheap on CPU | yes | ~8 s per 7 s clip, ~125 MB, ₹0 |
| Existing Ken Burns unchanged | required | **unchanged** (production engine called read-only) |
| Automated tests | green | **22/22** |

**Verdict: CONDITIONAL GO.** The motion quality, in my objective and visual
assessment, is good enough to be worth a limited opt-in beta. But per the
directive, production integration stays blocked until:

1. **The founder watches the three side-by-side videos** and approves the look
   (`char_sidebyside.mp4`, `village_sidebyside.mp4`, `complex_sidebyside.mp4`).
   I can measure smoothness; only a human can judge whether it *reads* as depth.
2. **A decision on camera energy** - keep the gentle 9 % push-in, or raise it to
   ~0.16-0.18 to match the Ken Burns hook (a one-line change, re-render ~25 s).
3. Ship **opt-in only** behind a `motion` flag with **Ken Burns as the default**
   and a guaranteed fallback on depth failure / `std(depth) < 0.02`.

This is deliberately short of an unconditional **GO**: nothing here justifies
flipping the production default, and the acceptance criterion that matters most
- a creator actually liking the motion - cannot be tested by me.

**No production integration has been performed.** Awaiting founder approval.

---

## Compliance

* No production file, database, schema, frontend component or cloud resource was
  modified; nothing was deployed or pushed.
* No paid API, GPU, extra model or binary was downloaded; no credits spent.
* All new work is under `experiments/depth_parallax/`; Phase-1/2 artifacts,
  including the original PoC MP4s, are preserved.
