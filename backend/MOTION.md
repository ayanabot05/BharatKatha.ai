# Camera motion engines

Two motion engines exist per scene. The default is unchanged and the 2.5D
engine is strictly opt-in.

| id | engine | default | notes |
|----|--------|---------|-------|
| `ken_burns` | FFmpeg `zoompan` | **yes** | Production behaviour. Fast. |
| `depth_parallax` | Real per-pixel 2.5D (see `motion.py`) | no | CPU. ~21 ms/frame after warm-up. |

## How it is selected

Per render request, not persisted in the schema:

```
POST /api/projects/{pid}/render
{ "motion": "depth_parallax" }        # omit for ken_burns
```

The value is stored as a plain top-level `motion` key on the project document
(schemaless - no migration). `GET /api/projects/motion/engines` reports which
engines are actually usable, so the Studio never offers 2.5D where it would do
nothing. The Studio toggle is labelled **Depth (2.5D)** and does not claim to
be generative video, because it is not.

## Fail-soft contract (do not remove)

`render.scene_clip` tries `depth_parallax` and on **any** exception - missing
model, missing `onnxruntime`, flat depth, OOM, ffmpeg failure - logs a warning
and renders that scene with Ken Burns instead.

A render must never fail, and a user must never see an error, because of this
engine. `motion.py` therefore raises ordinary exceptions and lets the caller
degrade. `motion.py` never writes user-facing error text.

## Per-scene quality gate

A scene whose depth map has `std < DEPTH_MIN_STD` (default `0.045`) is treated
as a single flat plane: parallax would only warp it, so it silently falls back.
`adaptive_strength()` additionally scales the displacement amplitude to how much
depth structure the scene actually has, so busy scenes move more than flat ones.

The finished render reports `render.motion` and `render.motion_fallbacks`, and
the completion message names how many scenes used the standard camera.

## Model

Depth Anything V2 Small (ONNX), **Apache-2.0 - commercially usable**.
Source: https://huggingface.co/onnx-community/depth-anything-v2-small
File: `onnx/model.onnx`, fp32, ~94 MB.

The weights are **not committed** to this repository. Resolution order:

1. `DEPTH_MODEL_PATH` environment variable
2. `backend/models/depth_anything_v2_small.onnx`  <- production location
3. `experiments/depth_parallax/models/...`        <- local dev fallback

## Environment

| Variable | Default | Purpose |
|----------|---------|---------|
| `DEPTH_MODEL_PATH` | - | Explicit path to the ONNX weights |
| `DEPTH_CACHE_DIR` | `backend/.depth_cache` | Depth map cache (content-hash keyed) |
| `DEPTH_THREADS` (or `DAP_THREADS`) | `2` | ONNX thread budget. Kept low so a render does not starve the API |
| `DEPTH_MIN_STD` | `0.045` | Flatness threshold for the quality gate |

## Deploy requirements

The 2.5D engine needs, **on the deployed host**:

* `onnxruntime` and `opencv-python-headless` importable by the running Python
  (they live in `backend/venv` locally - a server launched with a different
  interpreter will simply report `available: false` and fall back),
* the 94 MB ONNX file at `backend/models/` (or `DEPTH_MODEL_PATH`).

Neither is bundled. If they are missing the feature degrades silently rather
than breaking anything.

## Cost and caching

CPU only. No GPU, no network, no paid API. Depth costs ~2.5 s per scene the
first time; results are cached by SHA-256 of the prepared image, so a re-render
of an unchanged scene pays nothing. A 10-scene story adds ~25 s once.

## Provenance

Ported from the PoC in `experiments/depth_parallax` (Phase 1-3, verdict
CONDITIONAL GO, 78.2 -> 29.1 ms/frame after optimization). The copy is
deliberate: production must not import from an experiments folder.
Verify with `experiments/depth_parallax/verify_production.py`.
