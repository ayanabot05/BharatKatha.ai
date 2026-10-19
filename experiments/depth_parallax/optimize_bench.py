"""Benchmark the optimized parallax path against the original implementation.

  original  — depth_parallax.frame_from_grids (float vignette) = Phase-1 engine
  optimized — ParallaxScene.frame (integer vignette, precomputed field)
  fastdepth — ParallaxScene.frame(fast=True) (also skips the per-frame depth remap)

Reports per-frame cost and the pixel difference vs the original, plus the
benefit of cached depth maps.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np

EXP = Path(__file__).resolve().parent
REPO = EXP.parents[1]
sys.path.insert(0, str(EXP))
import depth_estimation as de  # noqa: E402
import depth_parallax as dp  # noqa: E402

SCENE = REPO / "test_reports" / "handover_dry_run" / "scene_1.png"
CACHE = EXP / "out" / "depth_cache"
N_FRAMES = 60


def main() -> int:
    import os
    os.environ.setdefault("DAP_THREADS", "2")
    import cv2
    cv2.setNumThreads(int(os.environ["DAP_THREADS"]))

    base = dp.fit_cover_bgr(SCENE)
    CACHE.mkdir(parents=True, exist_ok=True)
    key = hashlib.md5(SCENE.read_bytes()).hexdigest()[:16]
    cache_file = CACHE / f"{key}.npy"

    if cache_file.is_file():
        t0 = time.perf_counter()
        depth = np.load(cache_file).astype(np.float32)
        source, depth_s = "cache", round(time.perf_counter() - t0, 3)
    else:
        t0 = time.perf_counter()
        depth = de.smooth_depth(de.estimate_depth(base))
        np.save(cache_file, depth.astype(np.float16))
        source, depth_s = "computed", round(time.perf_counter() - t0, 2)

    strength = dp.adaptive_strength(depth)
    report = {"scene": str(SCENE.relative_to(REPO)), "frames": N_FRAMES,
              "depth_source": source, "depth_seconds": depth_s,
              "adaptive_strength": round(strength, 2)}

    scene = dp.ParallaxScene(base, depth, strength=strength, fast=False)
    scene_fast = dp.ParallaxScene(base, depth, strength=strength, fast=True)

    yy, xx = np.mgrid[0:base.shape[0], 0:base.shape[1]].astype(np.float32)
    vig = dp.vignette_mask(*base.shape[:2], 0.14)

    def original(t):
        return dp.frame_from_grids(base, depth, xx, yy, t, vig=vig, damp=scene.damp,
                                   amp_x=scene.amp_x, amp_y=scene.amp_y)

    def timeit(fn, n=N_FRAMES):
        fn(0.5)
        t0 = time.perf_counter()
        for i in range(n):
            fn(i / (n - 1))
        return round((time.perf_counter() - t0) / n * 1000, 1)

    report["original_ms_per_frame"] = timeit(original)
    report["optimized_ms_per_frame"] = timeit(scene.frame)
    report["fastdepth_ms_per_frame"] = timeit(scene_fast.frame)
    report["optimized_speedup_x"] = round(report["original_ms_per_frame"] / report["optimized_ms_per_frame"], 2)

    def diffs(a_fn, b_fn, label):
        out = []
        for t in (0.15, 0.5, 0.85):
            a = a_fn(t).astype(np.int16)
            b = b_fn(t).astype(np.int16)
            d = np.abs(a - b)
            out.append({"t": t, "mean": round(float(d.mean()), 3),
                        "max": int(d.max()), "p99": int(np.percentile(d, 99))})
        return {label: out}

    report.update(diffs(original, scene.frame, "optimized_vs_original_diff"))
    report.update(diffs(original, scene_fast.frame, "fastdepth_vs_original_diff"))

    (EXP / "out" / "optimize_bench.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
