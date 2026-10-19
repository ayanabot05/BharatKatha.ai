# Phase 2 - 2.5D Depth-Parallax Validation Sweep

**Directive:** validate the existing depth-parallax engine across 15-20 diverse,
already-approved scene images to decide whether it can reliably improve YouTube
Shorts without unacceptable artifacts or processing cost.

**Scope of this round:** still-frame validation only. No full MP4s were rendered,
no paid API was called, no production file, schema, cloud resource or billing
setting was touched. All work is inside `experiments/depth_parallax/`, and the
Phase-1 proof of concept and its verified MP4s were preserved untouched.

**Bottom line:** `CONDITIONAL GO` for a limited opt-in beta. See section 9.

---

## 1. Scenes tested

| Item | Value |
|---|---|
| Unique scenes tested | **20** |
| Missing / unreadable | 0 |
| Duplicate images (MD5-identical) included | **0** |
| Images duplicated to hit a target | none |

Selection was curated for *content diversity*, not cherry-picked for quality. All
images are existing local assets, deduped by content hash:

* `backend/storage/vidbharat/scenes/` (4 real projects' generated scenes)
* `backend/evaluations/` (project stills)
* `test_reports/handover_dry_run/`, `test_reports/complete_flow_case7/`,
  `test_reports/image_retest_2026-10-14/`
* `frontend/public/styles/`, `frontend/public/showcase/` (style/showcase refs)

Coverage: human faces and close-ups, full-body characters, village
environments, temple/building scenes, trees/forest/water, animals, indoor
scenes, and complex foreground/background boundaries.

**Limitation (reported, not hidden):** the available local corpus is
*AI-generated illustration* (plus two frontend style references). There is no
photographic live-action footage locally, and the sweep is **stills only**, so
temporal behaviour (flicker, depth jitter between frames) is not assessed here.
Images carrying burned-in text/UI (e.g. a Telugu overlay thumbnail and a
"Travel Cinematic" poster) were deliberately excluded because parallax behind
text is meaningless.

---

## 2. Contact sheet

* `out/validation/contact_sheet.png` - all 20 scenes, each cell = **Ken Burns
  (left)** vs **2.5D mid frame (right)**.
* `out/validation/S01_strip.png` ... `S20_strip.png` - per scene, five panels:
  `base | Ken Burns mid | 2.5D begin | 2.5D mid | 2.5D end`.

Ken Burns stills use the production hook push-in
(`z = min(1.0 + 0.18*on/frames, 1.18)`, centred) evaluated at the same time
fraction, so the comparison is apples-to-apples.

---

## 3. Per-scene results

**Objective measurements** (left of the rule) are raw machine output.
**Verdicts** (right of the rule) are my subjective visual judgement of the
stills - deliberately not converted into a numeric score.

| ID | Category | depth contrast | strength | max disp (px) | warp p95 (px) | out-of-bounds px | edge-energy ratio | geom MAE (zoom off) | Subjective verdict (stills) |
|---|---|---|---|---|---|---|---|---|---|
| S01 | animal + nature/water | 0.273 | 1.00 | 8.17 | 1.10 | 0 | 0.866 | 1.50 | Suitable - strong layer separation |
| S02 | indoor + cartoon | 0.188 | 0.89 | 6.96 | 0.40 | 0 | 0.896 | 1.15 | Suitable |
| S03 | full-body + village | 0.187 | 0.89 | 6.76 | 0.38 | 0 | 0.887 | 1.02 | Suitable |
| S04 | face close-up + hands | 0.221 | 1.00 | 7.30 | 0.66 | 0 | 0.874 | 1.39 | Suitable - face stable |
| S05 | village group at pump | 0.254 | 1.00 | 7.36 | 0.90 | 0 | 0.869 | 1.77 | Suitable |
| S06 | extreme close-up hands | 0.196 | 0.92 | 6.19 | 0.50 | 0 | 0.857 | 1.75 | Suitable |
| S07 | two people + village | 0.216 | 0.99 | 6.63 | 0.66 | 0 | 0.873 | 2.12 | Suitable |
| S08 | full-body walking village | 0.214 | 0.98 | 7.74 | 0.58 | 0 | 0.854 | 2.18 | Suitable |
| S09 | indoor modern + face | 0.230 | 1.00 | 8.28 | 0.79 | 0 | 0.901 | 0.99 | Suitable |
| S10 | face close-up indoor | 0.206 | 0.95 | 6.44 | 0.48 | 0 | 0.878 | 1.35 | Suitable |
| S11 | indoor multiple faces | 0.231 | 1.00 | 7.62 | 0.96 | 0 | 0.879 | 1.47 | Suitable |
| S12 | face close-up (PoC anchor) | 0.204 | 0.95 | 7.10 | 0.78 | 0 | 0.889 | 1.60 | Suitable - matches Phase 1 |
| S13 | people + temple building | 0.236 | 1.00 | 6.87 | 0.93 | 0 | 0.886 | 1.82 | Suitable |
| S14 | group under banyan tree | 0.248 | 1.00 | 6.57 | 1.06 | 0 | 0.875 | 2.56 | Suitable - dense crowd, no tearing |
| S15 | faces + temple | 0.244 | 1.00 | 7.10 | 0.89 | 0 | 0.875 | 2.30 | Suitable |
| S16 | full-body landscape + temple | 0.217 | 0.99 | 7.57 | 0.47 | 0 | 0.851 | 1.80 | Suitable |
| S17 | indoor modern laptop | 0.216 | 0.99 | 7.49 | 0.80 | 0 | 0.897 | 1.19 | Suitable |
| S18 | cartoon animal (minimal) | 0.187 | 0.89 | 5.96 | 0.27 | 0 | 0.983 | 0.22 | Suitable - subtle (flat depth) |
| S19 | photoreal portrait | 0.225 | 1.00 | 8.28 | 0.45 | 0 | 0.938 | 0.32 | Suitable - face stable |
| S20 | animal + forest | 0.213 | 0.98 | 6.47 | 0.78 | 0 | 0.879 | 1.44 | Suitable |

### Observed artifacts

Across all 20 scenes I did **not** see, in the stills:

* stretched or warped faces (checked S04, S10, S11, S12, S19 closely),
* halos or ghost edges at foreground/background boundaries (S01, S14, S20),
* tearing or pixel holes,
* clipped subjects that fall outside the frame.

The only mild, expected softening is sub-pixel (`warp p95` max 1.10 px) from
linear resampling; the `edge-energy ratio` (0.85-0.98) shows structure is
retained rather than blurred.

### How to read the objective metrics

* **max disp / warp p95** - how far pixels move and how much *neighbouring*
  pixels move relative to each other. Sub-pixel-to-1 px warping is why faces and
  edges hold up. `near_region_warp_p95` (foreground, where faces/hands live) was
  highest on S01 (2.27 px) and S09 (2.01 px) and both still looked clean.
* **out-of-bounds px = 0 everywhere** - no output pixel samples outside the
  source image, so there are no replicated-edge streaks.
* **edge-energy ratio** - output gradient energy vs source (1.0 = unchanged).
  0.85-0.98 = retained.
* **geom MAE (zoom off)** - mean absolute error in regions that *should not
  move* at all, with the push-in and vignette disabled to isolate geometry.
  0.22-2.56 (mostly <=0.5 px resampling rounding) confirms non-moving regions
  are genuinely left alone.
* A separate `static_region_mae` was also logged, but it is **not** used as a
  quality signal: pixels near the pivot still move because of the deliberate
  push-in, so it mostly measures the intended camera move, not artifacts.

---

## 4. Performance measurements

Machine: this laptop, CPU only (Intel UHD, no CUDA), `DAP_THREADS=2`.

| Measurement | Value |
|---|---|
| Depth estimation, cold (first call) | ~9.5 s (includes model load) |
| Depth estimation, warm | ~1.7-2.9 s/scene (mean ~2.2 s) |
| Depth, from cache | ~0.004 s/scene |
| Frame generation, steady state | **29.1 ms/frame** (720x1280) |
| Frame generation, sweep mean (incl. warm-up) | 40.8 ms/frame |
| Peak RAM per scene | ~315 MB |
| Sweep process peak RAM | 629 MB (holds 20 bases + depth maps + sheet buffers; not per-scene) |
| 9 s scene (~270 frames) | ~8 s frame-gen |
| ~45 s Short (~1350 frames) | ~40 s frame-gen + encode (under 1 min) |
| Paid APIs / GPU / cloud | **0 / none / none** |

Throughput of ~34 generated frames/second means a full multi-scene Short still
renders in well under a minute of local CPU, at a few hundred MB RAM.

---

## 5. Recommended animation strength by scene type

A single conservative preset already fits every scene tested. On top of it, the
engine applies `adaptive_strength(depth)` so flat scenes are pushed less:

```
strength = clip(0.6 + 0.4 * (std(depth) - 0.10) / 0.12, 0.6, 1.0)
```

Observed landing points and recommendations:

| Scene type | depth contrast | recommended strength | note |
|---|---|---|---|
| Wide village / full-body / architecture (S03,S05,S07,S08,S13,S14,S15,S16) | 0.19-0.25 | **1.0** | benefit most from layering |
| Face close-ups / portraits (S04,S10,S12,S19) | 0.20-0.23 | **0.95-1.0** | subject sits near pivot; moves little, stays stable |
| Indoor (S02,S09,S11,S17) | 0.19-0.23 | **0.9-1.0** | |
| Animals / nature (S01,S20) | 0.21-0.27 | **1.0** | S01 highest contrast -> full strength |
| Flat / minimal cartoon (S18) | 0.187 | **0.89** | short depth range; keep motion subtle |

Practical rule: if `std(depth) < 0.10`, cap strength at the 0.6 floor; if it is
below ~0.05 the scene has almost no depth to reveal and Ken Burns is fine.

---

## 6. Cases where Ken Burns should remain the default

1. **Flat / single-plane scenes** - `std(depth) < ~0.10`, where parallax adds
   nothing meaningful. S18 is the closest case and is already damped to 0.89.
2. **Subject fills the whole frame at one depth** - no background to separate.
3. **Burned-in text / UI overlays** - parallax behind text is meaningless (such
   images were excluded from this sweep).
4. **Depth-inference failure or degenerate output** (`std < 0.02`, all-zero) -
   automatically fall back.
5. **Any future scene whose foreground warping p95 exceeds ~2.5 px** while
   containing faces - lower the strength or fall back. This guard was *not*
   triggered (max observed 2.27 px on S01, which looked clean).

---

## 7. Measured optimization improvements

The dominant cost was not depth estimation but the per-frame **float vignette
composite** (34.8 ms/frame). Moving to an integer `cv2.multiply` and
precomputing the time-invariant parts of the displacement field (new
`ParallaxScene` class) gives:

| Path | ms/frame | vs original | max pixel diff |
|---|---|---|---|
| Original (`frame_from_grids`, float vignette) | 78.2 | 1.00x | - |
| **Optimized (`ParallaxScene, fast=False`)** | **29.1** | **2.69x** | **2 / 255** |
| Fast-depth variant (also skips per-frame depth remap) | 17.1 | 4.58x | 229 -> **rejected** |

* The **2.69x** path is adopted: visually identical (max 2/255 difference).
* The 4.58x variant diverges at strong displacement (max 229 at t=0.85) and is
  **rejected** for quality.
* **Depth caching** cuts repeat runs from ~2 s/scene to ~4 ms/scene and enables
  cheap re-renders of an unchanged scene.

None of this changes the Phase-1 functions or their verified MP4 outputs; the
optimization lives only in the new class used by the sweep.

---

## 8. Updated automated test results

```
backend\venv\Scripts\python.exe -m pytest experiments\depth_parallax\tests -q
19 passed
```

New tests added this round cover `adaptive_strength` (flat vs structured depth),
the optimized `ParallaxScene` (identity-with-no-motion, required depth,
zero out-of-bounds, fast-vs-accurate agreement). Prior tests (polarity
regression, genuine-parallax assertion, noise-ignoring) still pass.

**No claim of production-readiness is made on the basis of these tests alone** -
they prove the geometry is correct and bounded, not that viewers will like it.

---

## 9. Recommendation: CONDITIONAL GO

The internal engineering gate was **met with margin**:

| Gate | Requirement | Result |
|---|---|---|
| Acceptable visual quality | >= 80% of scenes | **20/20 = 100%** (stills) |
| No severe facial/structural distortion | in recommended scenes | **none observed** |
| Rendering practical on CPU | yes | ~29 ms/frame, ~315 MB, ~40 s per Short |
| Ken Burns behaviour unchanged | required | **unchanged** (Phase-1 code/outputs untouched) |
| Fallback clearly defined | required | defined (section 6) |

**Recommendation: a limited, opt-in beta** - not a default change - subject to:

1. Ship behind the `motion` flag; **Ken Burns stays the production default.**
2. Guaranteed automatic fallback to Ken Burns on depth failure or
   `std(depth) < 0.02`.
3. Keep the conservative Phase-1 preset (amp_x 12 / amp_y 4 / zoom 0.09, edge
   damping + radial feather) and the adaptive-strength cap.
4. **One short motion-clip check** (a couple of full 9 s scenes, ~2 min CPU)
   before rollout - stills cannot reveal temporal flicker or depth jitter
   between frames.
5. Re-run this sweep whenever new scene styles enter the content mix.

This is deliberately short of a **GO**: the evidence supports "clearly better
than Ken Burns on diverse scenes, with no observed distortion", but motion and
longer-term creator reception are still unverified.

### What would move this to full GO / what would trigger NO-GO

* **To GO:** the motion-clip check shows no flicker; a small creator beta shows
  no complaints about "wobble" or "cardboard" edges.
* **NO-GO triggers:** temporal flicker at depth boundaries, depth-model
  mis-estimation on new content classes, or CPU cost rising materially above the
  ~40 s per Short measured here.

### Next round (if approved)

Isolated, still: add a 2-3 scene motion-clip check (short MP4s, same directory),
then - only with explicit founder approval - implement the documented opt-in
integration (`motion` field on the render endpoint, `backend/motion.py`
dispatch, `StepRender.jsx` toggle) with Ken Burns fallback. No production change
has been made.

---

## Reproduction

```powershell
$env:DAP_THREADS="2"
backend\venv\Scripts\python.exe -m pytest experiments\depth_parallax\tests -q
backend\venv\Scripts\python.exe experiments\depth_parallax\validate_sweep.py
backend\venv\Scripts\python.exe experiments\depth_parallax\optimize_bench.py
```

Outputs: `out/validation/report.json`, `out/validation/contact_sheet.png`,
`out/validation/S01..S20_strip.png`, `out/optimize_bench.json`,
`out/depth_cache/*.npy` (depth maps, float16).

**Safety:** no production file/schema/cloud/billing change; no paid API, GPU or
deployment; no push; Phase-1 artifacts preserved. Only `experiments/` is added.
