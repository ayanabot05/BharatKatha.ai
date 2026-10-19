"""Run the 2.5D proof of concept and produce two comparable MP4s.

  Version A = the existing production engine (authentic Ken Burns via
              backend/render.py, imported read-only — nothing is modified).
  Version B = the experimental depth-parallax engine.

Both use the same source image, the same duration and the same 720x1280
resolution, so the comparison is like-for-like. Outputs land in ./out.

Nothing here touches the main app, the cloud, the database, or any paid API.
"""
from __future__ import annotations

import argparse
import ctypes
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

EXPERIMENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = EXPERIMENT_DIR.parents[1]
BACKEND = REPO_ROOT / "backend"
OUT_DIR = EXPERIMENT_DIR / "out"
DEFAULT_IMAGE = REPO_ROOT / "test_reports" / "handover_dry_run" / "scene_1.png"

sys.path.insert(0, str(EXPERIMENT_DIR))
sys.path.insert(0, str(BACKEND))


def _make_rss_probe():
    """Return a callable -> current working-set MB (Windows), or None if unavailable."""
    from ctypes import wintypes

    class PMC(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
            ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t),
        ]

    try:
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        k32.GetCurrentProcess.restype = wintypes.HANDLE
        fn = getattr(k32, "K32GetProcessMemoryInfo", None)
        if fn is None:
            fn = ctypes.WinDLL("psapi").GetProcessMemoryInfo
        fn.argtypes = [wintypes.HANDLE, ctypes.POINTER(PMC), wintypes.DWORD]
        fn.restype = wintypes.BOOL
    except Exception:
        return lambda: None

    def probe():
        pmc = PMC()
        pmc.cb = ctypes.sizeof(pmc)
        ok = fn(k32.GetCurrentProcess(), ctypes.byref(pmc), pmc.cb)
        return pmc.WorkingSetSize / 1048576.0 if ok else None

    return probe


_RSS = _make_rss_probe()


def _rss_mb() -> float | None:
    return _RSS()


class PeakRSS:
    """Sample working-set memory in a background thread, report the peak."""

    def __init__(self, interval: float = 0.05):
        self.interval = interval
        self._peak = 0.0
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def __enter__(self):
        self._peak = _rss_mb() or 0.0
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        return self

    def _loop(self):
        while not self._stop.is_set():
            v = _rss_mb()
            if v and v > self._peak:
                self._peak = v
            self._stop.wait(self.interval)

    def __exit__(self, *exc):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=1.0)
        return False

    @property
    def peak_mb(self) -> float | None:
        return round(self._peak, 1) if self._peak else None


def ffmpeg_exe() -> str:
    import imageio_ffmpeg

    return os.environ.get("FFMPEG_BINARY") or imageio_ffmpeg.get_ffmpeg_exe()


def render_version_a(src: Path, out: Path, duration: float, idx: int = 0) -> None:
    """Authentic existing engine: production prep_image + Ken Burns scene_clip."""
    import render as prod  # noqa: E402  (read-only import of production code)

    with tempfile.TemporaryDirectory(prefix="dap_a_") as td:
        work = Path(td)
        prepped = work / "prep.png"
        prod.prep_image(str(src), str(prepped))
        prod.scene_clip(str(prepped), duration, [], "te", str(out), idx, work)


def render_version_b(src: Path, depth, out: Path, duration: float, **kw) -> None:
    import depth_parallax

    depth_parallax.render_parallax(str(src), depth, str(out), duration, **kw)


def hstack(left: Path, right: Path, out: Path) -> None:
    subprocess.run(
        [ffmpeg_exe(), "-y", "-hide_banner", "-loglevel", "error", "-i", str(left), "-i", str(right),
         "-filter_complex", "[0:v][1:v]hstack=inputs=2[v]", "-map", "[v]",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", str(out)],
        check=True,
    )


def poster(left: Path, right: Path, out: Path, at: float) -> None:
    """Side-by-side still at time ``at`` seconds, with an A/B label burned in."""
    label_a = "A  Ken Burns"
    label_b = "B  Depth parallax"
    vf = (
        f"[0:v]drawtext=text='{label_a}':x=20:y=20:fontsize=40:fontcolor=white:box=1:boxcolor=black@0.6[a];"
        f"[1:v]drawtext=text='{label_b}':x=20:y=20:fontsize=40:fontcolor=white:box=1:boxcolor=black@0.6[b];"
        "[a][b]hstack=inputs=2[v]"
    )
    subprocess.run(
        [ffmpeg_exe(), "-y", "-hide_banner", "-loglevel", "error",
         "-ss", f"{at}", "-i", str(left), "-ss", f"{at}", "-i", str(right),
         "-filter_complex", vf, "-map", "[v]", "-frames:v", "1", str(out)],
        check=True,
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", default=str(DEFAULT_IMAGE))
    ap.add_argument("--duration", type=float, default=8.0, help="clip length in seconds")
    ap.add_argument("--amp-x", type=float, default=12.0)
    ap.add_argument("--amp-y", type=float, default=4.0)
    ap.add_argument("--zoom", type=float, default=0.09)
    ap.add_argument("--edge-damp", type=float, default=6.0)
    ap.add_argument("--smooth-sigma", type=float, default=0.12)
    ap.add_argument("--smooth-space", type=float, default=15.0)
    ap.add_argument("--smooth-diameter", type=int, default=15)
    ap.add_argument("--tag", default="", help="suffix for output filenames")
    args = ap.parse_args()

    os.environ.setdefault("DAP_THREADS", "2")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    src = Path(args.image)
    if not src.is_file():
        print(f"ERROR: source image not found: {src}", file=sys.stderr)
        return 2

    out_a = OUT_DIR / "version_a_kenburns.mp4"
    out_b = OUT_DIR / f"version_b_depth_parallax{args.tag}.mp4"
    out_side = OUT_DIR / f"side_by_side{args.tag}.mp4"
    out_depth = OUT_DIR / f"depth_map{args.tag}.png"
    out_poster = OUT_DIR / f"comparison_poster{args.tag}.png"

    import cv2
    import numpy as np
    import depth_estimation

    bench: dict = {
        "source_image": str(src),
        "duration_seconds": args.duration,
        "resolution": "720x1280",
        "fps": 30,
        "threads": os.environ.get("DAP_THREADS"),
        "params": {"amp_x": args.amp_x, "amp_y": args.amp_y, "zoom": args.zoom,
                   "edge_damp": args.edge_damp,
                   "depth_smooth": f"bilateral({args.smooth_diameter}, {args.smooth_sigma}, {args.smooth_space})"},
    }

    # --- Version B needs a depth map (measured on its own) --------------------
    from depth_parallax import fit_cover_bgr  # noqa: E402

    bgr = fit_cover_bgr(src)
    print("Estimating depth (Depth Anything V2 Small, CPU)...")
    with PeakRSS() as rss_b:
        t0 = time.perf_counter()
        depth_raw = depth_estimation.estimate_depth(bgr)
        depth = depth_estimation.smooth_depth(
            depth_raw, sigma_color=args.smooth_sigma, sigma_space=args.smooth_space,
            diameter=args.smooth_diameter)
        bench["depth_seconds"] = round(time.perf_counter() - t0, 2)
    bench["peak_rss_mb"] = rss_b.peak_mb
    cv2.imwrite(str(out_depth), depth_estimation.depth_preview(depth))
    bench["depth_map"] = str(out_depth)

    # --- Version A: existing engine ------------------------------------------
    print("Rendering Version A (existing Ken Burns engine)...")
    t0 = time.perf_counter()
    render_version_a(src, out_a, args.duration)
    bench["kenburns_seconds"] = round(time.perf_counter() - t0, 2)

    # --- Version B: experimental engine --------------------------------------
    print("Rendering Version B (depth parallax)...")
    t0 = time.perf_counter()
    render_version_b(src, depth, out_b, args.duration,
                     amp_x=args.amp_x, amp_y=args.amp_y, zoom=args.zoom,
                     edge_damp=args.edge_damp)
    bench["parallax_seconds"] = round(time.perf_counter() - t0, 2)

    # --- comparison artifacts -------------------------------------------------
    print("Building side-by-side comparison...")
    hstack(out_a, out_b, out_side)
    poster(out_a, out_b, out_poster, at=min(1.0, args.duration / 2))

    for p in (out_a, out_b, out_side, out_poster, out_depth):
        if not p.is_file() or p.stat().st_size == 0:
            print(f"ERROR: expected output missing/empty: {p}", file=sys.stderr)
            return 3
        bench.setdefault("outputs", {})[p.name] = p.stat().st_size

    (OUT_DIR / "benchmark.json").write_text(json.dumps(bench, indent=2), encoding="utf-8")
    print("\n=== BENCHMARK ===")
    print(json.dumps(bench, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
