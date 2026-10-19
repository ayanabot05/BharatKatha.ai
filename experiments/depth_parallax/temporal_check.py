"""Phase 3 - temporal quality inspection of the rendered motion samples.

For every clip it measures, frame by frame:
  * stream metadata + a full-decode check (bundled FFmpeg 7.1; the ffprobe
    binary is not bundled and was deliberately not downloaded),
  * frame-to-frame change (mean abs diff) and its jerk (2nd difference), to
    catch flicker and sudden jumps,
  * the darkest pixel in the outer border band, to catch black/missing pixels,
  * global translation between frames (phase correlation), to check the camera
    path is smooth and monotonic.

It also writes a 10-frame strip per 2.5D clip for visual inspection.
Separates objective measurements from the human judgement in the report.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import cv2

EXP = Path(__file__).resolve().parent
OUT = EXP / "out" / "phase3"
sys.path.insert(0, str(EXP))
from run_experiment import ffmpeg_exe  # noqa: E402

DURATION = 7.0
FPS = 30


def probe_ffmpeg(path: Path) -> dict:
    """Stream metadata from the bundled FFmpeg + a full-decode sanity check."""
    p = subprocess.run([ffmpeg_exe(), "-hide_banner", "-i", str(path)],
                       capture_output=True, text=True)
    txt = p.stderr
    info: dict = {"decodes_cleanly": False}
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", txt)
    if m:
        h, mm, ss = int(m.group(1)), int(m.group(2)), float(m.group(3))
        info["duration_s"] = round(h * 3600 + mm * 60 + ss, 2)
    m = re.search(r"Video:\s*(\w+)", txt)
    if m:
        info["codec"] = m.group(1)
    m = re.search(r"(\d{3,4})x(\d{3,4})", txt)
    if m:
        info["width"], info["height"] = int(m.group(1)), int(m.group(2))
    m = re.search(r"([\d.]+)\s*fps", txt)
    if m:
        info["fps"] = float(m.group(1))
    dec = subprocess.run([ffmpeg_exe(), "-v", "error", "-i", str(path), "-f", "null", "-"],
                         capture_output=True, text=True)
    info["decodes_cleanly"] = dec.returncode == 0 and dec.stderr.strip() == ""
    info["decode_stderr"] = dec.stderr.strip()[:300]
    return info


def analyse_clip(path: Path, strip_out: Path | None = None) -> dict:
    cap = cv2.VideoCapture(str(path))
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    prev_bgr = None
    prev_g = None
    f2f, shifts = [], []
    border_min = 255
    strip_idx = set(np.linspace(0, max(n - 1, 0), 10).astype(int).tolist()) if n else set()
    strip: list[np.ndarray] = []
    i = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        g = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        band = np.concatenate([frame[0], frame[-1], frame[:, 0], frame[:, -1]])
        border_min = min(border_min, int(band.min()))
        if prev_bgr is not None:
            f2f.append(float(np.abs(frame.astype(np.int16) - prev_bgr.astype(np.int16)).mean()))
            small = cv2.resize(prev_g, (w // 2, h // 2)).astype(np.float32)
            small2 = cv2.resize(g, (w // 2, h // 2)).astype(np.float32)
            (dx, dy), _ = cv2.phaseCorrelate(small, small2)
            shifts.append((float(dx), float(dy)))
        if i in strip_idx:
            sw = 120
            strip.append(cv2.resize(frame, (sw, int(sw * h / w))))
        prev_bgr, prev_g = frame, g
        i += 1
    cap.release()

    f2f_a = np.array(f2f) if f2f else np.array([0.0])
    jerk = float(np.abs(np.diff(f2f_a)).mean()) if len(f2f_a) > 1 else 0.0
    sh = np.array(shifts) if shifts else np.zeros((1, 2))
    dx = sh[:, 0]
    res = {
        "frames": i, "width": w, "height": h, "fps": round(fps, 3),
        "expected_frames": round(DURATION * FPS),
        "f2f_mae_mean": round(float(f2f_a.mean()), 3),
        "f2f_mae_median": round(float(np.median(f2f_a)), 3),
        "f2f_mae_max": round(float(f2f_a.max()), 3),
        "f2f_jump_ratio": round(float(f2f_a.max() / max(f2f_a.mean(), 1e-6)), 2),
        "jerk_mean": round(jerk, 3),
        "border_min_pixel": border_min,
        "shift_mean_px": round(float(np.hypot(dx, sh[:, 1]).mean()), 3),
        "shift_dx_std_px": round(float(dx.std()), 3),
        "shift_max_step_change_px": round(float(np.abs(np.diff(dx)).max()) if len(dx) > 1 else 0.0, 3),
    }
    if strip_out is not None and strip:
        hh = max(s.shape[0] for s in strip)
        canvas = np.full((hh + 20, sum(s.shape[1] for s in strip), 3), 18, np.uint8)
        x = 0
        for s in strip:
            canvas[20:20 + s.shape[0], x:x + s.shape[1]] = s
            x += s.shape[1]
        cv2.imwrite(str(strip_out), canvas)
        res["strip"] = str(strip_out.name)
    return res


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    report: dict = {"clips": {}}
    for p in sorted(OUT.glob("*.mp4")):
        if "_sidebyside" in p.name:
            continue
        strip = OUT / f"{p.stem}_frames.png" if p.name.endswith("_2p5d.mp4") else None
        print(f"analysing {p.name} ...")
        report["clips"][p.name] = {"probe": probe_ffmpeg(p), "temporal": analyse_clip(p, strip)}
    (OUT / "temporal_metrics.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
