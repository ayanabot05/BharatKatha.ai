"""Opt-in 2.5D depth-parallax motion for scene clips.

Genuine depth-based parallax, not a Ken Burns zoom/pan. For every output frame
a per-pixel coordinate field is built: each pixel is displaced sideways in
proportion to its estimated depth minus a pivot depth, so near surfaces move
one way and far surfaces the other way about the pivot. A slow zoom is layered
on top for a cinematic dolly.

This module is OFF by default. The production default stays ``ken_burns`` and
a caller must ask for ``depth_parallax`` explicitly. Nothing here runs unless
that mode is selected.

Provenance
----------
Ported from the validated proof of concept in ``experiments/depth_parallax``
(Phase 1-3, verdict CONDITIONAL GO, ~29 ms/frame after optimization). The copy
is deliberate: production must not import from an experiments folder.

Licensing
---------
Depth Anything V2 Small (ONNX) - Apache-2.0, commercially usable.
  Source: https://huggingface.co/onnx-community/depth-anything-v2-small
  File  : onnx/model.onnx, fp32, ~94 MB.
The weights are NOT committed to the repo. Resolution order is
``DEPTH_MODEL_PATH`` env var, then ``backend/models/depth_anything_v2_small.onnx``
(the documented production location), then the experiment fallback.

Fail-soft contract
------------------
Every failure in here (model missing, onnxruntime missing, flat depth, OOM,
ffmpeg error) raises an ordinary exception. ``render.scene_clip`` catches it and
silently produces a Ken Burns clip for that scene instead. A render must never
fail, and a user must never see an error, because of this module.

Cost
----
CPU only. No network, no paid API, no GPU. ~2.5 s per scene to estimate depth,
once; results are cached by image content hash so re-renders are free.
"""
from __future__ import annotations

import hashlib
import os
import subprocess
import time
from pathlib import Path

import cv2
import numpy as np

W, H, FPS = 720, 1280, 30
INPUT_SIZE = 518
_MEAN = np.array([0.485, 0.456, 0.406], np.float32)
_STD = np.array([0.229, 0.224, 0.225], np.float32)

MODEL_ID = "depth-anything-v2-small"
_BACKEND = Path(__file__).parent
MODEL_CANDIDATES = (
    _BACKEND / "models" / "depth_anything_v2_small.onnx",
    _BACKEND.parent / "experiments" / "depth_parallax" / "models" / "depth_anything_v2_small.onnx",
)

# Below this depth contrast a scene is effectively one flat plane. Pushing
# parallax on it only produces warping, so we defer to Ken Burns for that scene.
MIN_DEPTH_STD = float(os.environ.get("DEPTH_MIN_STD", "0.045"))

_session = None


class DepthUnavailable(RuntimeError):
    """Depth could not be produced for this scene. Caller must fall back."""


class DepthTooFlat(DepthUnavailable):
    """Depth was produced but has no structure to animate. Caller must fall back."""


# ---------------------------------------------------------------- model

def model_path() -> Path | None:
    override = os.environ.get("DEPTH_MODEL_PATH")
    if override:
        p = Path(override)
        return p if p.is_file() else None
    for candidate in MODEL_CANDIDATES:
        if candidate.is_file():
            return candidate
    return None


def available() -> bool:
    """True when depth can actually be produced on this machine."""
    if model_path() is None:
        return False
    try:
        import onnxruntime  # noqa: F401
    except Exception:
        return False
    return True


def _threads() -> int:
    """Small default thread budget so a render never starves the API."""
    raw = os.environ.get("DEPTH_THREADS") or os.environ.get("DAP_THREADS") or "2"
    try:
        return max(int(raw), 1)
    except ValueError:
        return 2


def get_session():
    global _session
    if _session is None:
        path = model_path()
        if path is None:
            raise DepthUnavailable(
                "Depth model missing. Set DEPTH_MODEL_PATH or place "
                "depth_anything_v2_small.onnx in backend/models/."
            )
        try:
            import onnxruntime as ort
        except Exception as exc:  # pragma: no cover - env dependent
            raise DepthUnavailable("onnxruntime is not installed") from exc
        opts = ort.SessionOptions()
        opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        opts.intra_op_num_threads = _threads()
        opts.inter_op_num_threads = 1
        _session = ort.InferenceSession(
            str(path), sess_options=opts, providers=["CPUExecutionProvider"]
        )
    return _session


def _tensor(rgb: np.ndarray) -> np.ndarray:
    x = rgb.transpose(2, 0, 1)[None].astype(np.float32)
    return np.ascontiguousarray((x - _MEAN[:, None, None]) / _STD[:, None, None])


def estimate_depth(raw: np.ndarray) -> np.ndarray:
    """Relative proximity in [0, 1] at input resolution. 1.0 = nearest.

    ``raw`` is an OpenCV BGR uint8 image. Depth Anything's raw output is
    monotonic in distance (larger = farther), so it is inverted here: the
    parallax renderer needs near pixels to receive the largest displacement.
    """
    if raw is None or getattr(raw, "size", 0) == 0:
        raise DepthUnavailable("estimate_depth: empty image")
    if raw.ndim != 3 or raw.shape[2] != 3:
        raise DepthUnavailable("estimate_depth: expected an HxWx3 BGR image")

    h, w = raw.shape[:2]
    rgb = cv2.cvtColor(raw, cv2.COLOR_BGR2RGB)
    small = cv2.resize(rgb, (INPUT_SIZE, INPUT_SIZE), interpolation=cv2.INTER_CUBIC)
    session = get_session()
    out = session.run(None, {session.get_inputs()[0].name: _tensor(small)})[0]
    depth = np.asarray(out[0], np.float32)
    depth = cv2.resize(depth, (w, h), interpolation=cv2.INTER_CUBIC)

    lo, hi = (float(v) for v in np.percentile(depth, (1.0, 99.0)))
    norm = np.clip((depth - lo) / max(hi - lo, 1e-6), 0.0, 1.0)
    return (1.0 - norm).astype(np.float32)


def smooth_depth(depth: np.ndarray, sigma_color: float = 0.08,
                 sigma_space: float = 9.0, diameter: int = 9) -> np.ndarray:
    """Edge-preserving denoise.

    The monocular model leaves speckle and soft gradients; left raw, per-pixel
    displacement turns that noise into visible warping. Bilateral filtering
    smooths within surfaces while keeping depth discontinuities sharp.
    """
    d = np.asarray(depth, np.float32)
    if d.size == 0:
        raise DepthUnavailable("smooth_depth: empty depth map")
    return cv2.bilateralFilter(d, diameter, sigma_color, sigma_space)


# ---------------------------------------------------------------- cache

def cache_dir() -> Path:
    root = os.environ.get("DEPTH_CACHE_DIR")
    path = Path(root) if root else _BACKEND / ".depth_cache"
    path.mkdir(parents=True, exist_ok=True)
    return path


def cache_key(image_path) -> str:
    h = hashlib.sha256()
    h.update(MODEL_ID.encode())
    h.update(str(INPUT_SIZE).encode())
    h.update(Path(image_path).read_bytes())
    return h.hexdigest()[:32]


def depth_for_image(image_path, bgr: np.ndarray | None = None) -> np.ndarray:
    """Depth for a scene image, cached by content hash.

    Cache misses cost ~2.5 s; a re-render of an unchanged scene is free.
    """
    key = cache_key(image_path)
    cached = cache_dir() / f"{key}.png"
    if cached.is_file():
        stored = cv2.imread(str(cached), cv2.IMREAD_GRAYSCALE)
        if stored is not None and stored.size:
            return (stored.astype(np.float32) / 255.0)

    base = bgr if bgr is not None else cv2.imread(str(image_path))
    if base is None:
        raise DepthUnavailable(f"could not read scene image: {image_path}")

    depth = smooth_depth(estimate_depth(base))
    cv2.imwrite(str(cached), np.clip(depth * 255.0, 0, 255).astype(np.uint8))
    return depth


# ---------------------------------------------------------------- quality

def depth_std(depth: np.ndarray) -> float:
    d = np.asarray(depth, np.float32)
    return float(np.std(d)) if d.size else 0.0


def quality_ok(depth: np.ndarray, minimum: float = None) -> bool:
    """False for flat / single-plane depth, where parallax would only warp."""
    return depth_std(depth) >= (MIN_DEPTH_STD if minimum is None else minimum)


def adaptive_strength(depth: np.ndarray, lo: float = 0.10, hi: float = 0.22,
                      floor: float = 0.6) -> float:
    """Scale animation amplitude to how much depth structure a scene has."""
    d = np.asarray(depth, np.float32)
    if d.size == 0:
        return floor
    s = (float(np.std(d)) - lo) / max(hi - lo, 1e-6)
    return float(np.clip(floor + (1.0 - floor) * s, floor, 1.0))


# ---------------------------------------------------------------- field math

def _smoothstep(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)


def edge_feather(shape, frac: float = 0.07) -> np.ndarray:
    """1.0 inside, ramping to 0.0 within ``frac`` of each border.

    Guarantees the remap never samples outside the image, so no torn edges.
    """
    h, w = shape[:2]
    b = max(int(round(min(h, w) * frac)), 1)
    ramp = _smoothstep(np.linspace(0.0, 1.0, b, dtype=np.float32))
    fy = np.ones(h, np.float32)
    fx = np.ones(w, np.float32)
    fy[:b], fy[h - b:] = ramp, ramp[::-1]
    fx[:b], fx[w - b:] = ramp, ramp[::-1]
    return (fy[:, None] * fx[None, :]).astype(np.float32)


def vignette_mask(h: int, w: int, strength: float = 0.14) -> np.ndarray:
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cx, cy = (w - 1) / 2.0, (h - 1) / 2.0
    r = np.sqrt(((xx - cx) / cx) ** 2 + ((yy - cy) / cy) ** 2) / np.sqrt(2.0)
    return (1.0 - strength * np.clip(r, 0.0, 1.0) ** 2).astype(np.float32)


def edge_damp(depth: np.ndarray, k: float = 6.0) -> np.ndarray:
    """Down-weight displacement where depth changes sharply.

    At a depth discontinuity (a person against a wall) a lateral shift tears
    the silhouette. Damping by the depth gradient keeps such structures intact.
    """
    d = np.asarray(depth, np.float32)
    gx = cv2.Sobel(d, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(d, cv2.CV_32F, 0, 1, ksize=3)
    mag = cv2.magnitude(gx, gy)
    return (1.0 / (1.0 + k * mag)).astype(np.float32)


def fit_cover_bgr(path_or_array, w: int = W, h: int = H) -> np.ndarray:
    """Aspect-preserving centre crop to w x h, matching production framing."""
    if isinstance(path_or_array, np.ndarray):
        src = path_or_array
        if src.shape[0] == h and src.shape[1] == w:
            return src
        from PIL import Image as _Image, ImageOps as _ImageOps
        im = _ImageOps.fit(_Image.fromarray(cv2.cvtColor(src, cv2.COLOR_BGR2RGB)), (w, h), _Image.LANCZOS)
        return cv2.cvtColor(np.array(im), cv2.COLOR_RGB2BGR)
    from PIL import Image as _Image, ImageOps as _ImageOps
    im = _ImageOps.fit(_Image.open(path_or_array).convert("RGB"), (w, h), _Image.LANCZOS)
    return cv2.cvtColor(np.array(im), cv2.COLOR_RGB2BGR)


class ParallaxScene:
    """Precompute the time-independent parts of the parallax field once."""

    def __init__(self, base, depth, *, amp_x=12.0, amp_y=4.0, zoom=0.09,
                 feather=0.07, damp_k=6.0, vignette=0.14, breath=0.012,
                 pivot=None, strength=1.0, fast=True):
        if depth is None:
            raise DepthUnavailable("ParallaxScene: a depth map is required")
        self.base = base
        self.h, self.w = base.shape[:2]
        self.depth = np.asarray(depth, np.float32)
        if self.depth.shape[:2] != (self.h, self.w):
            self.depth = cv2.resize(self.depth, (self.w, self.h), interpolation=cv2.INTER_LINEAR)
        self.pivot = float(np.median(self.depth)) if pivot is None else float(pivot)
        self.damp = edge_damp(self.depth, damp_k) if damp_k else np.ones_like(self.depth)
        self.fe = edge_feather((self.h, self.w), feather)
        self.vig = vignette_mask(self.h, self.w, vignette) if vignette else None
        self.vig_bgr = (np.repeat((self.vig * 255.0).astype(np.uint8)[..., None], 3, axis=2)
                        if self.vig is not None else None)
        self.amp_x = amp_x * strength
        self.amp_y = amp_y * strength
        self.zoom = zoom
        self.breath = breath
        self.fast = fast
        self.cx, self.cy = (self.w - 1) / 2.0, (self.h - 1) / 2.0
        self.yy, self.xx = np.mgrid[0:self.h, 0:self.w].astype(np.float32)
        self.xoff = (self.xx - self.cx).astype(np.float32)
        self.yoff = (self.yy - self.cy).astype(np.float32)
        disp_static = ((self.depth - self.pivot) * self.damp).astype(np.float32)
        self.dispfe_x = (self.amp_x * disp_static * self.fe).astype(np.float32)
        self.dispfe_y = (self.amp_y * disp_static * self.fe).astype(np.float32)

    def frame(self, t: float) -> np.ndarray:
        e = float(_smoothstep(np.array(t, np.float32)))
        lat = e * 2.0 - 1.0
        iz = 1.0 / (1.0 + self.zoom * e)
        xc = self.cx + self.xoff * iz
        yc = self.cy + self.yoff * iz
        if self.fast:
            dx, dy = self.dispfe_x, self.dispfe_y
        else:
            d_cam = cv2.remap(self.depth, xc, yc, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
            disp = (d_cam - self.pivot) * self.damp
            dx = self.amp_x * disp * self.fe
            dy = self.amp_y * disp * self.fe
        xs = xc + lat * dx
        ys = yc + lat * dy
        out = cv2.remap(self.base, xs, ys, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        if self.vig_bgr is not None:
            gain = (1.0 + self.breath * np.sin(2.0 * np.pi * t)) / 255.0
            out = cv2.multiply(out, self.vig_bgr, scale=gain)
        return out


# ---------------------------------------------------------------- clip

def scene_clip(img, dur, caps, lang, out, idx, work, ai_voice_disclosure=False):
    """Write one scene clip with depth-parallax motion and burned-in captions.

    Drop-in replacement for ``render.scene_clip``: identical output contract
    (720x1280, H.264, yuv420p, 30 fps) and the same caption pipeline, so clips
    from both engines concatenate cleanly in ``render.mux``.

    Raises ``DepthUnavailable`` / ``DepthTooFlat`` when the caller must fall
    back to Ken Burns.
    """
    if not available():
        raise DepthUnavailable("depth model or onnxruntime unavailable")

    import render as R  # local import: keeps this module dependency-light

    base = fit_cover_bgr(img)
    depth = depth_for_image(img, base)
    if not quality_ok(depth):
        raise DepthTooFlat(f"depth std {depth_std(depth):.3f} < {MIN_DEPTH_STD}")
    strength = adaptive_strength(depth)
    scene = ParallaxScene(base, depth, strength=strength)

    filters, node = [], "0:v"
    if caps:
        R.copy_caption_fonts(work, lang)
        ass = f"captions_{idx}.ass"
        R.caption_ass(caps, lang, work / ass)
        filters.append(f"[{node}]ass=filename={ass}:fontsdir=.[v1]")
        node = "v1"
    if ai_voice_disclosure:
        R.copy_caption_fonts(work, lang)
        ass = f"ai_voice_{idx}.ass"
        R.caption_ass([{"text": "AI-generated narration", "start": 0, "end": dur}],
                      lang, work / ass, placement="disclosure")
        nxt = f"v{len(filters) + 1}"
        filters.append(f"[{node}]ass=filename={ass}:fontsdir=.[{nxt}]")
        node = nxt

    n = max(int(round(dur * FPS)), 1)
    cmd = [
        R.FF, "-y", "-hide_banner", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{base.shape[1]}x{base.shape[0]}",
        "-r", str(FPS), "-i", "pipe:0",
    ]
    if filters:
        cmd += ["-filter_complex", ";".join(filters), "-map", f"[{node}]"]
    else:
        cmd += ["-map", "0:v"]
    cmd += ["-t", f"{dur:.2f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-pix_fmt", "yuv420p", "-r", str(FPS), str(out)]

    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, cwd=str(work))
    started = time.perf_counter()
    try:
        for i in range(n):
            proc.stdin.write(scene.frame(i / max(n - 1, 1)).tobytes())
    finally:
        if proc.stdin:
            proc.stdin.close()
        code = proc.wait()
    if code != 0:
        raise DepthUnavailable(f"parallax ffmpeg exited with {code}")

    elapsed = time.perf_counter() - started
    return {"mode": "depth_parallax", "strength": round(strength, 2),
            "depth_std": round(depth_std(depth), 3), "frames": n,
            "seconds": round(elapsed, 2), "ms_per_frame": round(elapsed / n * 1000.0, 1)}
