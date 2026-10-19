"""Phase 3 - real 2.5D motion samples vs Ken Burns, for three diverse scenes.

For each of three scenes (human character / Indian village / complex
environment) this produces:

    <key>_2p5d.mp4        depth-parallax clip  (optimized ParallaxScene)
    <key>_kenburns.mp4    the existing production Ken Burns engine
    <key>_sidebyside.mp4  labelled A/B comparison

720x1280, 30 fps, H.264, 7 s each. Local CPU only. No paid API, no GPU, no
production code or cloud change. Outputs land in ./out/phase3.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

EXP = Path(__file__).resolve().parent
REPO = EXP.parents[1]
OUT = EXP / "out" / "phase3"
CACHE = EXP / "out" / "depth_cache"
sys.path.insert(0, str(EXP))
sys.path.insert(0, str(REPO / "backend"))

import numpy as np  # noqa: E402
import cv2  # noqa: E402

import depth_estimation as de  # noqa: E402
import depth_parallax as dp  # noqa: E402
from run_experiment import PeakRSS, ffmpeg_exe, render_version_a  # noqa: E402

# key, role, Phase-2 id, source image (relative to repo root)
SCENES = [
    ("char", "human character (face close-up + hands)", "S04",
     r"backend\storage\vidbharat\scenes\46057842e877488e9a6c7200aa1f29a5\04a2a7c2217e406a884d9d1540f1f693.png"),
    ("village", "Indian village / landscape (full-body, walking)", "S08",
     r"backend\storage\vidbharat\scenes\aafb74931f004c7a969391bf4edccdfa\2cd86277eeeb4f24a6c75ea3ed831c0c.png"),
    ("complex", "complex environment (group under banyan tree)", "S14",
     r"test_reports\handover_dry_run\scene_4.png"),
]

DURATION = 7.0
FPS = 30


def side_by_side(left: Path, right: Path, out: Path) -> None:
    vf = (
        "[0:v]drawtext=text='A  Ken Burns':x=18:y=16:fontsize=34:fontcolor=white:"
        "box=1:boxcolor=black@0.6[a];"
        "[1:v]drawtext=text='B  2.5D parallax':x=18:y=16:fontsize=34:fontcolor=white:"
        "box=1:boxcolor=black@0.6[b];[a][b]hstack=inputs=2[v]"
    )
    subprocess.run(
        [ffmpeg_exe(), "-y", "-hide_banner", "-loglevel", "error",
         "-i", str(left), "-i", str(right), "-filter_complex", vf, "-map", "[v]",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
         "-pix_fmt", "yuv420p", str(out)],
        check=True,
    )


def depth_for(path: Path, base: np.ndarray) -> tuple[np.ndarray, float, bool]:
    import hashlib

    CACHE.mkdir(parents=True, exist_ok=True)
    key = hashlib.md5(path.read_bytes()).hexdigest()[:16]
    cache_file = CACHE / f"{key}.npy"
    if cache_file.is_file():
        return np.load(cache_file).astype(np.float32), 0.0, True
    t0 = time.perf_counter()
    depth = de.smooth_depth(de.estimate_depth(base))
    np.save(cache_file, depth.astype(np.float16))
    return depth, round(time.perf_counter() - t0, 2), False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--duration", type=float, default=DURATION)
    args = ap.parse_args()

    os.environ.setdefault("DAP_THREADS", "2")
    cv2.setNumThreads(int(os.environ["DAP_THREADS"]))
    OUT.mkdir(parents=True, exist_ok=True)

    bench = {"duration_seconds": args.duration, "resolution": "720x1280", "fps": FPS,
             "threads": os.environ["DAP_THREADS"], "scenes": []}

    for key, role, sid, rel in SCENES:
        src = REPO / rel
        if not src.is_file():
            print(f"ERROR: missing source {src}", file=sys.stderr)
            return 2
        print(f"\n=== {key}: {role}  [{sid}] ===")

        base = dp.fit_cover_bgr(src)
        depth, depth_s, cached = depth_for(src, base)
        strength = dp.adaptive_strength(depth)
        print(f"  depth {'cache' if cached else 'computed'} ({depth_s}s)  strength={strength:.2f}")

        scene = dp.ParallaxScene(base, depth, strength=strength)

        out_25d = OUT / f"{key}_2p5d.mp4"
        out_kb = OUT / f"{key}_kenburns.mp4"
        out_side = OUT / f"{key}_sidebyside.mp4"

        # --- 2.5D (optimized engine) -----------------------------------------
        cpu0, wall0 = time.process_time(), time.perf_counter()
        with PeakRSS() as rss:
            info = scene.render_video(out_25d, args.duration, fps=FPS)
        wall_25d = time.perf_counter() - wall0
        cpu_25d = time.process_time() - cpu0
        print(f"  2.5D   {wall_25d:5.1f}s wall  {info['ms_per_frame']:4.1f} ms/frame  "
              f"peak {rss.peak_mb} MB")

        # --- Ken Burns (authentic production engine) -------------------------
        wall0 = time.perf_counter()
        with PeakRSS() as rss_kb:
            render_version_a(src, out_kb, args.duration)
        wall_kb = time.perf_counter() - wall0
        print(f"  KenB   {wall_kb:5.1f}s wall   peak {rss_kb.peak_mb} MB")

        # --- comparison -------------------------------------------------------
        side_by_side(out_kb, out_25d, out_side)
        cv2.imwrite(str(OUT / f"{key}_depth.png"), de.depth_preview(depth))

        bench["scenes"].append({
            "key": key, "role": role, "phase2_id": sid, "source": rel,
            "adaptive_strength": round(strength, 2),
            "depth_seconds": depth_s, "depth_cached": cached,
            "amp_x": round(scene.amp_x, 2), "amp_y": round(scene.amp_y, 2), "zoom": scene.zoom,
            "pivot": round(scene.pivot, 4),
            "two5d": {"wall_seconds": round(wall_25d, 2), **info,
                      "python_cpu_percent": round(cpu_25d / wall_25d * 100, 1),
                      "peak_rss_mb": rss.peak_mb,
                      "bytes": out_25d.stat().st_size},
            "kenburns": {"wall_seconds": round(wall_kb, 2),
                         "peak_rss_mb": rss_kb.peak_mb,
                         "bytes": out_kb.stat().st_size},
            "side_by_side_bytes": out_side.stat().st_size,
        })

    (OUT / "motion_benchmark.json").write_text(json.dumps(bench, indent=2), encoding="utf-8")
    print("\n=== BENCHMARK ===")
    print(json.dumps(bench, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
