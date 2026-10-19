"""Generate browser-ready AI depth maps for the landing-page phone demo.

Runs the already-validated Depth Anything V2 Small ONNX model (Apache-2.0,
CPU, local, zero cost) over the five showcase stills and writes 8-bit
grayscale proximity maps into ``frontend/public/depth/``.

Polarity: 255 = nearest surface, 0 = farthest. This matches
``depth_estimation.estimate_depth`` (1.0 == nearest), so the browser can use
the map directly to drive a per-pixel 2.5D displacement.

Run:  $env:DAP_THREADS="2"; backend\\venv\\Scripts\\python.exe make_web_depth.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import depth_estimation as de  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "frontend" / "public" / "showcase"
OUT = ROOT / "frontend" / "public" / "depth"
TARGET_W = 420
COUNT = 5


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    report: dict[str, dict] = {}

    for i in range(COUNT):
        src = SRC / f"s{i}.jpg"
        img = cv2.imread(str(src))
        if img is None:
            print(f"MISSING {src}")
            continue

        started = time.time()
        depth = de.smooth_depth(de.estimate_depth(img))
        h, w = depth.shape
        scale = TARGET_W / float(w)
        small = cv2.resize(
            depth, (TARGET_W, max(1, int(round(h * scale)))), interpolation=cv2.INTER_AREA
        )
        png = (np.clip(small, 0.0, 1.0) * 255.0).round().astype(np.uint8)

        dst = OUT / f"s{i}.png"
        if not cv2.imwrite(str(dst), png):
            raise RuntimeError(f"could not write {dst}")

        elapsed = time.time() - started
        report[f"s{i}"] = {
            "src": f"/showcase/s{i}.jpg",
            "depth": f"/depth/s{i}.png",
            "w": int(png.shape[1]),
            "h": int(png.shape[0]),
            "min": int(png.min()),
            "max": int(png.max()),
            "mean": round(float(png.mean()), 1),
            "std": round(float(png.std()), 1),
            "seconds": round(elapsed, 2),
        }
        print(
            f"s{i}: {png.shape[1]}x{png.shape[0]} "
            f"min={png.min()} max={png.max()} mean={png.mean():.1f} std={png.std():.1f} "
            f"({elapsed:.1f}s)"
        )

    (OUT / "index.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"wrote {OUT / 'index.json'} ({len(report)} maps)")


if __name__ == "__main__":
    main()
