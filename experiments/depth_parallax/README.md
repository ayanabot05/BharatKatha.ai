# 2.5D Cinematic Video Engine — Proof of Concept

**Status:** working local PoC. **Scope:** experimental only — no production code,
no database, no cloud deploy, no paid API, no billing changes.

This implements a genuine **depth-based parallax** renderer as an *optional*
alternative to the existing Ken Burns engine, and proves it against the real
engine on a real approved scene from this repository.

---

## 1. What is here

```
experiments/depth_parallax/
├── depth_estimation.py     Depth Anything V2 Small (ONNX) -> proximity map
├── depth_parallax.py       Per-pixel depth-parallax renderer (OpenCV + FFmpeg)
├── run_experiment.py       Produces Version A vs Version B + benchmark
├── tests/test_depth_parallax.py   14 isolated tests (all passing)
├── models/                 depth_anything_v2_small.onnx (94.5 MB, Apache-2.0, git-ignored)
└── out/                    sample MP4s, stills, depth map, benchmark.json (git-ignored)
```

Nothing outside `experiments/depth_parallax/` was created or modified.

---

## 2. Reproduce

```powershell
# from repo root; no installs needed (onnxruntime + opencv + ffmpeg already present)
$py = "backend\venv\Scripts\python.exe"
$env:DAP_THREADS = "2"                     # keep the laptop responsive

# run the isolated tests
& $py -m pytest experiments\depth_parallax\tests -q

# produce Version A (existing engine) and Version B (2.5D), plus benchmark
& $py experiments\depth_parallax\run_experiment.py --duration 8
```

The model is fetched once, only if missing:

```powershell
# https://huggingface.co/onnx-community/depth-anything-v2-small  (Apache-2.0)
# onnx/model.onnx — fp32, 94.5 MB
```

Delete everything afterwards (recovers ~100 MB, nothing else depends on it):

```powershell
Remove-Item -Recurse -Force experiments\depth_parallax
```

---

## 3. Outputs (verified)

| File | What |
|---|---|
| `out/version_a_kenburns.mp4` | Existing engine, same image/duration |
| `out/version_b_depth_parallax.mp4` | Experimental 2.5D engine |
| `out/side_by_side.mp4` | A and B played next to each other |
| `out/comparison_poster.png`, `out/poster_t4.png`, `out/poster_t7.png` | A/B stills |
| `out/depth_map.png` | Predicted proximity map (bright = near) |
| `out/benchmark.json` | Raw timings and memory |

All three MP4s verified by probe: **720×1280 (A/B) and 1440×1280 (side-by-side),
8.00 s, 30 fps, H.264 yuv420p, no audio track.**

---

## 4. Architecture assessment — what exists, what was reused

From the read-only audit (`docs/PROJECT_MASTER_PLAN.md:20`, `backend/render.py:1-15`,
`backend/projects.py:1203-1252`):

* Video today is **`backend/render.py`**: `camera_motion()` -> `scene_clip()`
  (FFmpeg `zoompan` Ken Burns) -> `mux()` (concat + narration + optional BGM).
  Output is 720×1280, 30 fps, H.264.
* The PoC **reuses the real production Ken Burns** for Version A by importing
  `backend/render.py` read-only (`prep_image` + `scene_clip`) — the existing
  engine is exercised unmodified.
* The PoC **reuses the production encode settings** (libx264, `veryfast`, crf 23,
  yuv420p, 30 fps) so Version B drops straight into the same pipeline shape.
* The render system already has clean seams: per-scene clip generation in
  `scene_clip()`, a concatenation/mux step, and durable Cloud Run Job dispatch
  (`cloud_render_dispatch.py`, `cloud_scene_dispatch.py`). No new architecture
  is required to adopt 2.5D.

---

## 5. How the 2.5D engine works

1. **Depth** — Depth Anything V2 Small ONNX, CPU, 518×518 input. The raw output
   is monotonic in *distance* (larger = farther); it is inverted to a
   **proximity map** (1.0 = nearest). Found and fixed during the PoC: without the
   flip the background over-moves and the depth cue is wrong.
2. **Smoothing** — a bilateral filter removes model speckle while keeping depth
   discontinuities.
3. **Parallax** — per output frame, each pixel is displaced horizontally/vertically
   by `amp × camera(t) × (proximity − pivot)`. Near and far surfaces move by
   different amounts in opposite directions about the pivot — the defining cue
   of 2.5D, which a zoom/pan cannot produce. A slow push-in is layered on top.
4. **Artifact guards** —
   * **edge damping**: displacement is scaled down where the depth gradient is
     high, so silhouettes and pillars don't tear;
   * **radial edge feather**: displacement -> 0 at the frame border, so the remap
     never samples outside the image and cannot expose torn edges.

No claim is made that this produces human body motion. It is scene parallax plus
camera motion.

---

## 6. Performance benchmark (this laptop, 2 CPU threads)

| Metric | Version A (Ken Burns) | Version B (2.5D) |
|---|---|---|
| Depth inference + smoothing | — | **3.0 s** |
| Render (8 s clip, 240 frames) | **3.6 s** | **29.3 s** |
| Peak process RAM | — | **315 MB** |
| Output | 720×1280, 8 s, H.264 | 720×1280, 8 s, H.264 |
| Paid API calls | 0 | **0** |
| Disk footprint (whole PoC incl. model) | — | **~103 MB** |

Both engines are practical on CPU. Version B is ~8× the render cost of Ken Burns
per scene — still seconds, not minutes, for a whole Short.

---

## 7. Visual quality assessment

**Advantages**
* Genuine multi-layer separation: the subject and the courtyard move differently,
  which reads as depth in motion rather than a flat zoom.
* The cinematography feels less mechanical than a single Ken Burns push-in.
* Subject remains well preserved with the conservative defaults.

**Artifacts / limitations (honest)**
* Thin vertical structures (the pillar) show a mild smear at depth edges.
* A faint halo can appear where a near object meets the background.
* Monocular depth on **hand-drawn/illustrated** frames is approximate and blobby;
  it is better on photographic-realistic frames.
* Non-rigid surfaces (wrinkled cloth) can shear under larger displacement — this
  is why amplitude is kept modest.
* A single image still cannot animate a person. This is parallax, not motion.

**Verdict:** with the conservative preset (`amp_x=12`, `edge_damp=6`,
`bilateral(15, 0.12, 15)`) the result is a clear improvement over Ken Burns and
does **not** look broken. At higher amplitude (`amp_x≈30`, the first attempt) the
face and pillar visibly deformed — that preset was rejected.

---

## 8. Integration proposal (not implemented — for approval)

Nothing below is done; it documents the exact minimal change.

**Backend**
* Add `backend/motion.py` exposing `render_scene(image, duration, out, *, mode, idx, work)`
  with `mode ∈ {"ken_burns", "depth_parallax"}`. `ken_burns` delegates to the
  existing `render.scene_clip`; `depth_parallax` runs depth + parallax. This keeps
  the production renderer untouched by default.
* In `backend/projects.py::_render_job` (the per-scene loop) call `motion.render_scene`
  instead of `scene_clip` directly, reading `project.get("motion", "ken_burns")`.
* `POST /projects/{pid}/render` accepts an optional `motion` field.
* **Scene schema:** add optional `depth_path` / `video_path`. **Additive and
  nullable — no migration** (Supabase columns or JSON fields added lazily). Existing
  projects default to `ken_burns` and render exactly as today.

**Frontend**
* In `frontend/src/studio/StepRender.jsx` add a two-option control
  ("Cinematic 2.5D" / "Classic") sent in the render POST; show a small badge on
  the finished video. Default stays Classic.

**Safety**
* Feature-flag the option; fall back to `ken_burns` if the depth model is missing
  or fails, exactly as the current engine is the guaranteed path.

---

## 9. Cloud Run Job path (documented only — NOT deployed)

Depth is CPU-only, so this fits the existing serverless CPU footprint:

* Build a job image containing `onnxruntime`, `opencv-python-headless`, FFmpeg and
  the 94.5 MB model; reuse the token-auth pattern from `deploy/image-worker/app.py`
  and the dispatch pattern from `backend/cloud_render_dispatch.py`.
* Run the job with 4–8 vCPU / 4 GiB so depth and FFmpeg run in one pass; no GPU,
  no new always-on service, scale-to-zero.
* Copy `out/` media to the existing GCS bucket; the main API stays stateless.

No cloud resource was created, modified, or billed during this PoC.

---

## 10. Cost assessment

| Component | Local PoC | In production |
|---|---|---|
| Depth model (Depth Anything V2 Small) | $0 (Apache-2.0) | $0 |
| Depth inference | $0, CPU | ~3 s of Cloud Run CPU per scene |
| Parallax render | $0, CPU | ~30 s of Cloud Run CPU per scene |
| Paid video/image/voice API | **none** | **none** |
| Storage | ~1 MB/scene | a few MB in the existing GCS bucket |

Marginal cost per scene is a fraction of a cent of Cloud Run CPU — the same order
as the current render. There is no GPU and no per-second vendor charge.

---

## 11. Next-phase recommendation

**Do not promote to production yet.** Recommended, in order:

1. **Validate breadth** — run the stills-only comparison over 15–20 diverse
   approved scenes and confirm no catastrophic cases.
2. **Batch depth per project** — depth is per scene; batch it inside the render
   job to keep total project time low.
3. **Tune per scene** — auto-lower amplitude when depth confidence/contrast is low.
4. **Ship as opt-in beta** behind the `motion` flag with guaranteed Ken Burns
   fallback, and watch real creator feedback before making it the default.
5. Keep the door open to true generative motion (GPU/Veo/Varya) as a later,
   separate decision — this PoC does not reopen that roadmap.

---

## 12. Compliance notes

* No production file, database, migration, IAM, quota or cloud service was changed.
* No paid API, no GPU, no deployment, no push.
* Model is Apache-2.0 (commercially usable); size 94.5 MB — verified before download.
* All tests are isolated under `experiments/depth_parallax/tests`.

---

## 13. Phase 2 — multi-scene still-frame validation sweep

Per the founder directive, the engine was validated across **20 unique, diverse
local scene images** (still frames only — no MP4s; no paid API; no production
change). Full write-up: **[`PHASE2_REPORT.md`](PHASE2_REPORT.md)**.

Run it yourself (low CPU, depth maps cached):

```powershell
$env:DAP_THREADS="2"
backend\venv\Scripts\python.exe experiments\depth_parallax\validate_sweep.py
backend\venv\Scripts\python.exe experiments\depth_parallax\optimize_bench.py
```

Artifacts: `out/validation/report.json`, `out/validation/contact_sheet.png`,
`out/validation/S01..S20_strip.png`.

### Headline results

| Metric | Value |
|---|---|
| Unique scenes tested | 20 (0 missing, 0 duplicates) |
| Out-of-bounds / missing pixels | **0** in every scene |
| Geometric warping, p95 | 0.27 – 1.10 px (mean 0.69) |
| Structure retained (edge-energy ratio) | 0.85 – 0.98 |
| Tearing where nothing should move (zoom off) | MAE 0.22 – 2.56 (isolated ≤0.5 px rounding) |
| Subjective suitability (stills) | 20 / 20 acceptable; **no** facial or structural distortion seen |
| Automated tests | **19 / 19 passing** |

### Measured optimization (adopted)

| Path | ms/frame (720×1280, 2 threads) | vs original | Max pixel diff |
|---|---|---|---|
| Original (float vignette) | 78.2 | 1.00× | — |
| **Optimized (integer vignette + precomputed field)** | **29.1** | **2.69×** | **2** |
| Fast-depth variant (also skips per-frame depth remap) | 17.1 | 4.58× | 229 -> rejected |

The optimization is a **2.69× speed-up that is visually identical** (max 2/255
pixel difference). It lives in the new `ParallaxScene` class; the Phase-1
functions (`frame_from_grids`, `render_parallax`) and their MP4 outputs are
untouched. Cached depth maps cut repeat runs from ~2 s/scene to ~4 ms.

### Verdict update

**CONDITIONAL GO** for a limited opt-in beta (Ken Burns default unchanged),
with a clearly defined fallback and one short motion-clip check before rollout.
See `PHASE2_REPORT.md` for per-scene results, strength guidance and the
Ken-Burns-stays-default list.

---

## 14. Phase 3 - real motion samples

Three 7 s clips were rendered with the optimized engine, each with a Ken Burns
comparison and a labelled side-by-side (720x1280, 30 fps, H.264). Full write-up:
**[`PHASE3_REPORT.md`](PHASE3_REPORT.md)**.

```powershell
$env:DAP_THREADS="2"
backend\venv\Scripts\python.exe experiments\depth_parallax\render_motion.py
backend\venv\Scripts\python.exe experiments\depth_parallax\temporal_check.py
```

Outputs: `out/phase3/{char,village,complex}_{2p5d,kenburns,sidebyside}.mp4`
plus `<key>_keyframes_compare.png`, `motion_benchmark.json`,
`temporal_metrics.json`, `ffmpeg_probe_report.json`.

| Clip | f2f MAE mean | jerk mean | jump ratio | face/structure |
|---|---|---|---|---|
| `char_2p5d` | 0.72 | 0.10 | 1.62 | preserved |
| `village_2p5d` | 1.33 | 0.09 | 1.56 | preserved |
| `complex_2p5d` | 1.28 | 0.09 | 1.53 | preserved |
| Ken Burns (same scenes) | 2.90-6.00 | 0.79-2.31 | 1.55-1.73 | - |

No flicker, jumps, tearing, halos or introduced black borders; 2.5D is ~3x the
wall time of Ken Burns (~8 s vs ~2.6 s per 7 s clip, ~125 MB, CPU only).
Caveat: the 2.5D preset (9 % push-in) is gentler than the Ken Burns hook (18 %).

**Verdict: CONDITIONAL GO** - founder must watch the side-by-side videos and
approve before any integration. Ken Burns remains the production default.
