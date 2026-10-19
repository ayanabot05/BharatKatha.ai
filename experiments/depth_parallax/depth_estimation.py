"""Depth Anything V2 Small (ONNX) CPU depth estimation.

Experimental module for the 2.5D proof of concept. It is NOT imported by any
production code path.

Model
-----
Source : https://huggingface.co/onnx-community/depth-anything-v2-small
License: Apache-2.0 (commercially usable)
File   : onnx/model.onnx, fp32, 94.5 MB
Input  : pixel_values [1, 3, H, W] float32, ImageNet-normalised RGB
Output : predicted_depth [1, h, w] float32. The raw model output is monotonic
         in distance (larger = farther). ``estimate_depth`` inverts it and
         returns a relative PROXIMITY map in [0, 1] (1.0 = nearest), which is
         what the parallax renderer needs.

Reference preprocessing for Depth Anything V2 is a direct resize to 518x518
(a multiple of the ViT patch size 14), RGB, mean=[0.485,0.456,0.406],
std=[0.229,0.224,0.225]. The output is relative, not metric, which is exactly
what we need for parallax: it only has to rank pixels by depth.
"""
from __future__ import annotations

import os
from pathlib import Path

import cv2
import numpy as np

MODEL_PATH = Path(__file__).parent / "models" / "depth_anything_v2_small.onnx"
INPUT_SIZE = 518
_MEAN = np.array([0.485, 0.456, 0.406], np.float32)
_STD = np.array([0.229, 0.224, 0.225], np.float32)

_session = None


def _blank_chw(rgb: np.ndarray) -> np.ndarray:
    x = rgb.transpose(2, 0, 1)[None].astype(np.float32)
    return np.ascontiguousarray((x - _MEAN[:, None, None]) / _STD[:, None, None])


def get_session():
    """Create the ONNX Runtime CPU session once per process."""
    global _session
    if _session is None:
        if not MODEL_PATH.is_file():
            raise FileNotFoundError(
                f"Depth model missing: {MODEL_PATH}. "
                "Download onnx-community/depth-anything-v2-small (Apache-2.0)."
            )
        import onnxruntime as ort

        opts = ort.SessionOptions()
        opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        # Keep the laptop responsive: default to a small thread budget.
        threads = int(os.environ.get("DAP_THREADS", "2"))
        opts.intra_op_num_threads = max(threads, 1)
        opts.inter_op_num_threads = 1
        _session = ort.InferenceSession(
            str(MODEL_PATH), sess_options=opts, providers=["CPUExecutionProvider"]
        )
    return _session


def estimate_depth(raw: np.ndarray) -> np.ndarray:
    """Return normalised relative proximity in [0, 1] at the input resolution.

    ``raw`` is an OpenCV BGR uint8 image. Output is float32, same H x W,
    where 1.0 is the nearest surface and 0.0 the farthest.
    """
    if raw is None or getattr(raw, "size", 0) == 0:
        raise ValueError("estimate_depth: empty image")
    if raw.ndim != 3 or raw.shape[2] != 3:
        raise ValueError("estimate_depth: expected an HxWx3 BGR image")

    h, w = raw.shape[:2]
    rgb = cv2.cvtColor(raw, cv2.COLOR_BGR2RGB)
    small = cv2.resize(rgb, (INPUT_SIZE, INPUT_SIZE), interpolation=cv2.INTER_CUBIC)
    tensor = _blank_chw(small)

    session = get_session()
    out = session.run(None, {session.get_inputs()[0].name: tensor})[0]
    depth = np.asarray(out[0], np.float32)
    depth = cv2.resize(depth, (w, h), interpolation=cv2.INTER_CUBIC)

    lo, hi = (float(v) for v in np.percentile(depth, (1.0, 99.0)))
    norm = np.clip((depth - lo) / max(hi - lo, 1e-6), 0.0, 1.0)
    # Depth Anything's raw output is monotonic in *distance* (larger = farther).
    # Return a proximity map instead — 1.0 = nearest — which is what the
    # parallax renderer expects (near pixels must receive the largest shift).
    return (1.0 - norm).astype(np.float32)


def depth_preview(depth: np.ndarray) -> np.ndarray:
    """Colourised BGR preview of a depth map (nearest = warm)."""
    gray = np.clip(np.asarray(depth, np.float32) * 255.0, 0, 255).astype(np.uint8)
    return cv2.applyColorMap(gray, cv2.COLORMAP_INFERNO)


def smooth_depth(depth: np.ndarray, sigma_color: float = 0.08, sigma_space: float = 9.0,
                 diameter: int = 9) -> np.ndarray:
    """Edge-preserving denoise of a raw depth map.

    The monocular model leaves speckle and soft gradients. Left raw, per-pixel
    displacement turns that noise into visible warping. A bilateral filter
    smooths within surfaces while keeping sharp depth discontinuities, which is
    what we want before parallax.
    """
    d = np.asarray(depth, np.float32)
    if d.size == 0:
        raise ValueError("smooth_depth: empty depth map")
    return cv2.bilateralFilter(d, diameter, sigma_color, sigma_space)
