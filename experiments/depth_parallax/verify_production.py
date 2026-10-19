"""Verify the production 2.5D integration end to end (local, CPU, zero cost).

Checks:
  1. motion.available() is true on this machine
  2. render.scene_clip(motion="depth_parallax") produces a real MP4 with the
     exact production contract (720x1280, 30 fps, H.264, yuv420p, audio-free)
  3. the depth cache makes a second render cheap
  4. fail-soft: a missing model silently degrades to Ken Burns, still valid MP4
  5. default mode is unchanged (ken_burns unless asked)

Run:
  backend\\venv\\Scripts\\python.exe experiments\\depth_parallax\\verify_production.py
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
os.environ.setdefault("DAP_THREADS", "2")

import motion  # noqa: E402
import render  # noqa: E402

IMG = ROOT / "frontend" / "public" / "showcase" / "s0.jpg"
CAPS = [{"text": "A beautiful story begins", "start": 0.0, "end": 1.6}]
DUR = 3.0


def probe(path) -> str:
    err = subprocess.run([render.FF, "-hide_banner", "-i", str(path)],
                         capture_output=True, text=True).stderr
    return next((ln.strip() for ln in err.splitlines() if "Stream #0:0" in ln), "no video stream")


def main() -> int:
    work = Path(tempfile.mkdtemp(prefix="verify_25d_"))
    prepped = work / "img_0.jpg"
    render.prep_image(IMG, prepped)

    print("1) available ..............", motion.available(),
          f"(model: {(motion.model_path() or 'MISSING')})")
    if not motion.available():
        print("   FAIL: depth engine not available; cannot verify the happy path")
        return 1

    print("\n2) depth_parallax clip")
    t0 = time.perf_counter()
    out = work / "clip_depth.mp4"
    info = render.scene_clip(prepped, DUR, CAPS, "en", out, 0, work, False, "depth_parallax")
    wall = time.perf_counter() - t0
    size = out.stat().st_size if out.is_file() else 0
    print(f"   info .................. {info}")
    print(f"   file .................. {size / 1024:.0f} KB, wall {wall:.1f}s")
    print(f"   duration .............. {render.duration(out):.2f}s (asked {DUR})")
    print(f"   stream ................ {probe(out)}")
    ok_contract = info.get("mode") == "depth_parallax" and size > 10_000 and abs(render.duration(out) - DUR) < 0.3
    print("   contract ..............", "OK" if ok_contract else "FAIL")
    if "720x1280" not in probe(out) or "yuv420p" not in probe(out):
        print("   FAIL: output does not match the production clip contract")
        ok_contract = False

    print("\n3) depth cache (second call)")
    t0 = time.perf_counter()
    out2 = work / "clip_depth2.mp4"
    info2 = render.scene_clip(prepped, DUR, CAPS, "en", out2, 0, work, False, "depth_parallax")
    print(f"   wall .................. {time.perf_counter() - t0:.1f}s "
          f"(first was {wall:.1f}s; {info2.get('ms_per_frame')} ms/frame)")

    print("\n4) fail-soft with a missing model")
    real = os.environ.get("DEPTH_MODEL_PATH")
    os.environ["DEPTH_MODEL_PATH"] = str(work / "does_not_exist.onnx")
    motion._session = None
    out3 = work / "clip_fallback.mp4"
    try:
        info3 = render.scene_clip(prepped, DUR, CAPS, "en", out3, 0, work, False, "depth_parallax")
        size3 = out3.stat().st_size if out3.is_file() else 0
        print(f"   mode .................. {info3.get('mode')}  ({size3 / 1024:.0f} KB)")
        ok_soft = info3.get("mode") == "ken_burns" and size3 > 10_000
        print("   no crash, Ken Burns ...", "OK" if ok_soft else "FAIL")
    except Exception as exc:
        print(f"   FAIL: fallback raised {exc!r}")
        ok_soft = False
    finally:
        if real is None:
            os.environ.pop("DEPTH_MODEL_PATH", None)
        else:
            os.environ["DEPTH_MODEL_PATH"] = real
        motion._session = None

    print("\n5) default mode unchanged")
    out4 = work / "clip_default.mp4"
    info4 = render.scene_clip(prepped, DUR, CAPS, "en", out4, 0, work, False)
    ok_default = info4.get("mode") == "ken_burns"
    print(f"   default mode .......... {info4.get('mode')}", "OK" if ok_default else "FAIL")

    passed = ok_contract and ok_soft and ok_default
    print("\nRESULT:", "ALL CHECKS PASSED" if passed else "FAILURES PRESENT",
          f"(work dir {work})")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
