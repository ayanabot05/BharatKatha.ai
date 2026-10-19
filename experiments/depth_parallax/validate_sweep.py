"""Phase 2 — still-frame validation sweep over diverse local scene images.

For each unique scene it:
  * estimates (and caches) a depth map,
  * renders three representative 2.5D stills (begin / middle / end),
  * builds a still from the existing Ken Burns move for comparison,
  * measures objective metrics (displacement, warping, out-of-bounds pixels,
    edge energy, face-region warping) and timings,
  * writes per-scene strips plus a master contact sheet.

No MP4s are rendered. No paid API. No production file is touched.
Outputs go to ./out/validation.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import cv2
from PIL import Image, ImageDraw

EXP = Path(__file__).resolve().parent
REPO = EXP.parents[1]
OUT = EXP / "out" / "validation"
CACHE = EXP / "out" / "depth_cache"
sys.path.insert(0, str(EXP))

import depth_estimation as de  # noqa: E402
import depth_parallax as dp  # noqa: E402
from run_experiment import PeakRSS  # noqa: E402

T_BEGIN, T_MID, T_END = 0.08, 0.50, 0.92

# Curated for diversity. id, category, path (relative to repo root).
SCENES = [
    ("S01", "animal + nature/water",      r"backend\storage\vidbharat\scenes\39a5abfb05a64ce9815249e2b3de87ba\645e7bb8daa74a179300740220fa091d.png"),
    ("S02", "indoor + cartoon",           r"backend\storage\vidbharat\scenes\39a5abfb05a64ce9815249e2b3de87ba\85695c1b896c44faa9e12152d8ece511.png"),
    ("S03", "full-body + village motion", r"backend\storage\vidbharat\scenes\39a5abfb05a64ce9815249e2b3de87ba\cd946013030b4e5c9df11764116f991b.png"),
    ("S04", "face close-up + hands",      r"backend\storage\vidbharat\scenes\46057842e877488e9a6c7200aa1f29a5\04a2a7c2217e406a884d9d1540f1f693.png"),
    ("S05", "village group at pump",      r"backend\storage\vidbharat\scenes\46057842e877488e9a6c7200aa1f29a5\2488792d8948496589bd1f21195864d7.png"),
    ("S06", "extreme close-up hands",     r"backend\storage\vidbharat\scenes\46057842e877488e9a6c7200aa1f29a5\b93e0fe503e04267842c405282a09a22.png"),
    ("S07", "two people + village",       r"backend\storage\vidbharat\scenes\8340b82521d6471095fd52f9024d1917\15c89148215d4a1797a0dd2024e9f4cf.png"),
    ("S08", "full-body walking village",  r"backend\storage\vidbharat\scenes\aafb74931f004c7a969391bf4edccdfa\2cd86277eeeb4f24a6c75ea3ed831c0c.png"),
    ("S09", "indoor modern + face",       r"backend\evaluations\ayana_codex_scene_1.png"),
    ("S10", "face close-up indoor",       r"backend\evaluations\ayana_codex_scene_3.png"),
    ("S11", "indoor multiple faces",      r"backend\evaluations\ayana_scene_2.png"),
    ("S12", "face close-up (PoC anchor)", r"test_reports\handover_dry_run\scene_1.png"),
    ("S13", "people + temple building",   r"test_reports\handover_dry_run\scene_2.png"),
    ("S14", "group under banyan tree",    r"test_reports\handover_dry_run\scene_4.png"),
    ("S15", "faces + temple",             r"test_reports\complete_flow_case7\scene_1.png"),
    ("S16", "full-body landscape+temple", r"test_reports\complete_flow_case7\scene_4.png"),
    ("S17", "indoor modern laptop",       r"test_reports\image_retest_2026-10-14\bird_edit.png"),
    ("S18", "cartoon animal (minimal)",   r"frontend\public\styles\animals.jpg"),
    ("S19", "photoreal portrait",         r"frontend\public\styles\human.jpg"),
    ("S20", "animal + forest",            r"frontend\public\showcase\s0.jpg"),
]

def ken_burns_still(base: np.ndarray, t: float) -> np.ndarray:
    """Still of the production Ken Burns hook move (render.camera_motion(0)).

    Production uses zoompan z = min(1.0 + 0.18*on/frames, 1.18) centered.
    Evaluated analytically at fraction ``t`` of the clip.
    """
    z = 1.0 + 0.18 * float(t)
    h, w = base.shape[:2]
    cx, cy = (w - 1) / 2.0, (h - 1) / 2.0
    m = np.float32([[1 / z, 0, cx - cx / z], [0, 1 / z, cy - cy / z]])
    return cv2.warpAffine(base, m, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)


def edge_energy(img: np.ndarray) -> float:
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
    return float(cv2.magnitude(cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3),
                               cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3)).mean())


def analyse(base: np.ndarray, depth: np.ndarray) -> dict:
    strength = dp.adaptive_strength(depth)
    scene = dp.ParallaxScene(base, depth, strength=strength)
    mid = scene.frame(T_MID)
    disp = scene.displacement_px(1.0)

    field = scene.disp_static * scene.amp_x
    gy, gx = np.gradient(field)
    warp = np.sqrt(gx * gx + gy * gy)

    # Region-based warping proxies (no face model available in OpenCV 5 headless).
    # Foreground detail (nearest depth) is what carries faces and hands.
    d = np.asarray(depth, np.float32)
    near = d <= np.percentile(d, 15)
    far = d >= np.percentile(d, 85)
    near_warp = round(float(np.percentile(warp[near], 95)), 2) if near.any() else None
    far_warp = round(float(np.percentile(warp[far], 95)), 2) if far.any() else None

    static_mask = disp < 0.5
    static_mae = (round(float(np.abs(mid.astype(np.int16) - base.astype(np.int16)).mean(axis=2)[static_mask].mean()), 2)
                  if static_mask.any() else None)

    return {
        "depth_contrast": round(float(np.std(depth)), 3),
        "adaptive_strength": round(strength, 2),
        "disp_max_px": round(float(disp.max()), 2),
        "disp_mean_px": round(float(disp.mean()), 2),
        "warp_p95_px": round(float(np.percentile(warp, 95)), 2),
        "warp_max_px": round(float(warp.max()), 2),
        "out_of_bounds_px": scene.out_of_bounds(1.0),
        "edge_energy_ratio": round(edge_energy(mid) / max(edge_energy(base), 1e-6), 3),
        "static_region_mae": static_mae,
        "near_region_warp_p95_px": near_warp,
        "far_region_warp_p95_px": far_warp,
    }, scene


def label_panel(img: np.ndarray, text: str, width: int = 200) -> Image.Image:
    p = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    p.thumbnail((width, 4000))
    canvas = Image.new("RGB", (p.width, p.height + 22), (16, 16, 20))
    canvas.paste(p, (0, 22))
    ImageDraw.Draw(canvas).text((4, 5), text, fill=(255, 235, 120))
    return canvas


def hstack_panels(panels: list[Image.Image]) -> Image.Image:
    h = max(p.height for p in panels)
    w = sum(p.width for p in panels)
    out = Image.new("RGB", (w, h), (16, 16, 20))
    x = 0
    for p in panels:
        out.paste(p, (x, 0))
        x += p.width
    return out


def main() -> int:
    import os

    os.environ.setdefault("DAP_THREADS", "2")
    cv2.setNumThreads(int(os.environ["DAP_THREADS"]))
    OUT.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)

    results, missing = [], []
    mid_pairs = []
    print(f"Validation sweep: {len(SCENES)} scenes (stills only)")
    with PeakRSS() as rss:
        for sid, category, rel in SCENES:
            path = REPO / rel
            if not path.is_file():
                missing.append(rel)
                print(f"  {sid} MISSING {rel}")
                continue
            t0 = time.perf_counter()
            base = dp.fit_cover_bgr(path)

            key = hashlib.md5(path.read_bytes()).hexdigest()[:16]
            cache_file = CACHE / f"{key}.npy"
            cached = cache_file.is_file()
            if cached:
                depth = np.load(cache_file).astype(np.float32)
                depth_s = 0.0
            else:
                td = time.perf_counter()
                probe = de.estimate_depth(base)
                depth = de.smooth_depth(probe)
                np.save(cache_file, depth.astype(np.float16))
                depth_s = round(time.perf_counter() - td, 2)

            m, scene = analyse(base, depth)

            # three representative frames + Ken Burns + base
            frames = {t: scene.frame(t) for t in (T_BEGIN, T_MID, T_END)}
            tf = time.perf_counter()
            _ = scene.frame(0.5)
            frame_ms = round((time.perf_counter() - tf) * 1000, 1)
            kb = ken_burns_still(base, T_MID)

            panels = [label_panel(base, f"{sid} base"),
                      label_panel(kb, "Ken Burns mid"),
                      label_panel(frames[T_BEGIN], "2.5D begin"),
                      label_panel(frames[T_MID], "2.5D mid"),
                      label_panel(frames[T_END], "2.5D end")]
            hstack_panels(panels).save(OUT / f"{sid}_strip.png")

            mid_pairs.append((sid, kb, frames[T_MID]))
            results.append({
                "id": sid, "category": category, "path": rel, **m,
                "depth_seconds": depth_s, "frame_ms": frame_ms,
                "total_seconds": round(time.perf_counter() - t0, 2),
            })
            print(f"  {sid} {category:<28} depth={depth_s:>4}s frame={frame_ms:>6}ms "
                  f"disp_max={m['disp_max_px']:>5} warp_p95={m['warp_p95_px']:>4} "
                  f"oob={m['out_of_bounds_px']} near={m['near_region_warp_p95_px']} cached={cached}")

    # master contact sheet: 5 columns of [Ken Burns | 2.5D mid] pairs
    cols, cell = 5, 150
    rows = (len(mid_pairs) + cols - 1) // cols
    cw, ch = cell * 2, int(cell * 16 / 9) + 22
    sheet = Image.new("RGB", (cols * cw, rows * ch), (16, 16, 20))
    d = ImageDraw.Draw(sheet)
    for i, (sid, kb, mid) in enumerate(mid_pairs):
        pair = hstack_panels([label_panel(kb, "KB", cell), label_panel(mid, "2.5D", cell)])
        sheet.paste(pair, ((i % cols) * cw, (i // cols) * ch))
        d.text(((i % cols) * cw + 4, (i // cols) * ch + 4), sid, fill=(120, 255, 180))
    sheet.save(OUT / "contact_sheet.png")

    summary = {
        "scenes_tested": len(results),
        "missing": missing,
        "peak_rss_mb": rss.peak_mb,
        "depth_cache_entries": len(list(CACHE.glob("*.npy"))),
        "total_depth_seconds_fresh": round(sum(r["depth_seconds"] for r in results), 1),
        "mean_frame_ms": round(float(np.mean([r["frame_ms"] for r in results])), 1),
        "any_out_of_bounds": sum(r["out_of_bounds_px"] for r in results),
        "mean_warp_p95_px": round(float(np.mean([r["warp_p95_px"] for r in results])), 2),
        "scenes_with_out_of_bounds": sum(1 for r in results if r["out_of_bounds_px"] > 0),
    }
    (OUT / "report.json").write_text(json.dumps({"summary": summary, "scenes": results}, indent=2), encoding="utf-8")
    print("\n=== SUMMARY ===")
    print(json.dumps(summary, indent=2))
    print("wrote:", OUT / "contact_sheet.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
