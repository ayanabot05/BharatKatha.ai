"""Isolated tests for the 2.5D depth-parallax proof of concept.

Run:  backend/venv/Scripts/python -m pytest experiments/depth_parallax/tests -q

These tests do not touch production code, the network, the database or any
paid API. The one test that needs the depth model is skipped if it is absent.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest
import cv2

EXP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXP))

import depth_estimation  # noqa: E402
import depth_parallax as dp  # noqa: E402


def _photo(h=180, w=120):
    """A synthetic 'scene': bright block (near) over a dark gradient (far)."""
    img = np.zeros((h, w, 3), np.uint8)
    grad = np.linspace(20, 120, h, dtype=np.uint8)
    img[:, :, 0] = grad[:, None]
    img[:, :, 1] = grad[:, None]
    img[:, :, 2] = grad[:, None]
    img[h // 3:h // 2, w // 4:w // 2] = (255, 255, 255)
    return img


# --------------------------------------------------------------------------- #
# depth_estimation
# --------------------------------------------------------------------------- #

def test_estimate_depth_shape_and_range():
    depth = depth_estimation.estimate_depth(_photo())
    assert depth.shape == (180, 120)
    assert depth.dtype == np.float32
    assert 0.0 <= float(depth.min()) and float(depth.max()) <= 1.0
    assert not np.isnan(depth).any()


def test_estimate_depth_empty_raises():
    with pytest.raises(ValueError):
        depth_estimation.estimate_depth(np.zeros((0, 0, 3), np.uint8))


def test_estimate_depth_bad_shape_raises():
    with pytest.raises(ValueError):
        depth_estimation.estimate_depth(np.zeros((10, 10), np.uint8))


def test_depth_polarity_near_is_higher():
    """A near object must score higher proximity than the far background.

    Guards the inversion bug found during the PoC: the raw model output is
    monotonic in distance, so it must be flipped before parallax.
    """
    img = np.zeros((300, 300, 3), np.uint8)
    cv2.circle(img, (150, 150), 90, (255, 255, 255), -1)
    d = depth_estimation.estimate_depth(img)
    assert float(d[150, 150]) > float(d[10, 10])


def test_missing_model_is_reported(monkeypatch):
    depth_estimation._session = None
    monkeypatch.setattr(depth_estimation, "MODEL_PATH", Path("does_not_exist.onnx"))
    with pytest.raises(FileNotFoundError):
        depth_estimation.get_session()
    depth_estimation._session = None


# --------------------------------------------------------------------------- #
# depth_parallax geometry
# --------------------------------------------------------------------------- #

def test_edge_feather_interior_one_border_zero():
    fe = dp.edge_feather((100, 100), 0.1)
    assert fe.shape == (100, 100)
    assert pytest.approx(1.0, abs=1e-6) == float(fe[50, 50])
    assert float(fe[0, 50]) < 0.01
    assert float(fe[50, 0]) < 0.01


def test_vignette_center_bright_corner_dark():
    v = dp.vignette_mask(100, 100, 0.2)
    assert float(v[50, 50]) > 0.99
    assert float(v[0, 0]) < 0.9


def test_smooth_depth_preserves_shape_and_range():
    rng = np.random.default_rng(0)
    d = np.clip(rng.random((80, 60)).astype(np.float32), 0, 1)
    s = depth_estimation.smooth_depth(d)
    assert s.shape == d.shape and s.dtype == np.float32
    assert 0.0 <= float(s.min()) and float(s.max()) <= 1.0


def test_smooth_depth_empty_raises():
    with pytest.raises(ValueError):
        depth_estimation.smooth_depth(np.zeros((0, 0), np.float32))


def test_edge_damp_flat_vs_step():
    flat = np.full((60, 60), 0.5, np.float32)
    assert float(dp.edge_damp(flat).min()) > 0.99          # no damping inside a surface
    step = np.zeros((60, 60), np.float32)
    step[:, 30:] = 1.0
    assert float(dp.edge_damp(step).min()) < 0.5           # strong damping at a depth edge


def test_identity_when_no_motion():
    """amp and zoom at zero must return (almost) the untouched base image."""
    base = _photo(120, 90)
    depth = np.full((120, 90), 0.5, np.float32)
    fr = dp.frame_at(base, depth, 0.5, amp_x=0, amp_y=0, zoom=0.0, vig=None, breath=0)
    assert fr.shape == base.shape and fr.dtype == np.uint8
    assert np.abs(fr.astype(int) - base.astype(int)).mean() < 2.0


def test_depth_displacement_is_genuine_parallax():
    """Near pixels must move more than far pixels — the core 2.5D requirement."""
    h, w = 240, 160
    base = np.full((h, w, 3), 40, np.uint8)
    base[:, 10:26] = (235, 235, 235)     # a bar in the far half
    base[:, 118:134] = (235, 235, 235)   # a bar in the near half
    depth = np.full((h, w), 0.30, np.float32)
    depth[:, 80:] = 1.00                 # right half is near, left half is far

    kw = dict(amp_x=40, amp_y=0, zoom=0.0, vig=None, breath=0.0, pivot=0.5)
    f0 = dp.frame_at(base, depth, 0.0, **kw)
    f1 = dp.frame_at(base, depth, 1.0, **kw)

    def bar_x(frame, lo, hi):
        col = frame[:, lo:hi].astype(np.float32).mean(axis=(0, 2))
        return lo + int(np.argmax(col))

    d_far = bar_x(f1, 0, 60) - bar_x(f0, 0, 60)
    d_near = bar_x(f1, 80, 160) - bar_x(f0, 80, 160)

    assert d_near != 0, "near content must move"
    assert abs(d_near) > abs(d_far), "near must move more than far"
    assert (d_near > 0) != (d_far > 0) or d_far == 0, "near and far move apart, not together"


def test_missing_depth_raises():
    with pytest.raises(ValueError):
        dp.frame_at(_photo(), None, 0.5)
    with pytest.raises(ValueError):
        dp.render_parallax(_photo(), None, "x.mp4", 1.0)


def test_render_writes_playable_mp4(tmp_path):
    """End-to-end: a short clip encodes, and leaves no stray temp files."""
    src = tmp_path / "in.png"
    import cv2
    cv2.imwrite(str(src), _photo(240, 135))
    depth = np.tile(np.linspace(0, 1, 135, dtype=np.float32), (240, 1))
    out = tmp_path / "clip.mp4"
    dp.render_parallax(str(src), depth, str(out), 0.5, vignette=0.1)
    assert out.is_file() and out.stat().st_size > 1000
    leftover = [p.name for p in tmp_path.iterdir() if p.suffix not in {".png", ".mp4"}]
    assert leftover == [], f"unexpected temp files: {leftover}"


# --------------------------------------------------------------------------- #
# adaptive strength + optimized scene
# --------------------------------------------------------------------------- #

def test_adaptive_strength_flat_vs_structured():
    flat = np.full((80, 80), 0.5, np.float32)
    structured = np.zeros((80, 80), np.float32)
    structured[:, 40:] = 1.0
    assert dp.adaptive_strength(flat) < 0.7               # low contrast -> damped
    assert dp.adaptive_strength(structured) == pytest.approx(1.0, abs=1e-6)


def test_parallax_scene_identity_no_motion():
    base = _photo(120, 90)
    depth = np.full((120, 90), 0.5, np.float32)
    scene = dp.ParallaxScene(base, depth, amp_x=0, amp_y=0, zoom=0.0, vignette=0, breath=0)
    fr = scene.frame(0.5)
    assert fr.shape == base.shape and fr.dtype == np.uint8
    assert np.abs(fr.astype(int) - base.astype(int)).mean() < 2.0


def test_parallax_scene_requires_depth():
    with pytest.raises(ValueError):
        dp.ParallaxScene(_photo(60, 40), None)


def test_parallax_scene_no_out_of_bounds_pixels():
    base = _photo(240, 135)
    depth = np.tile(np.linspace(0, 1, 135, dtype=np.float32), (240, 1))
    scene = dp.ParallaxScene(base, depth, amp_x=20, amp_y=8)
    assert scene.out_of_bounds(1.0) == 0


def test_parallax_scene_fast_matches_full():
    """The fast path must stay visually close to the accurate path."""
    base = _photo(240, 135)
    depth = np.tile(np.linspace(0, 1, 135, dtype=np.float32), (240, 1))
    fast = dp.ParallaxScene(base, depth, fast=True).frame(0.8)
    full = dp.ParallaxScene(base, depth, fast=False).frame(0.8)
    assert np.abs(fast.astype(int) - full.astype(int)).mean() < 3.0


# --------------------------------------------------------------------------- #
# motion quality (Phase 3)
# --------------------------------------------------------------------------- #

def _striped_scene(h=180, w=120):
    base = np.zeros((h, w, 3), np.uint8)
    base[:, :, 0] = np.linspace(60, 220, w, dtype=np.uint8)[None, :]
    base[:, :, 1] = np.linspace(60, 220, h, dtype=np.uint8)[:, None]
    base[:, :, 2] = 160
    for x in range(0, w, 14):
        base[:, x:x + 5] = (235, 210, 170)
    depth = np.tile(np.linspace(0.0, 1.0, w, dtype=np.float32), (h, 1))
    return base, depth


def test_parallax_scene_motion_is_temporally_smooth():
    """Frame-to-frame change must be steady: motion, but no sudden jumps."""
    base, depth = _striped_scene()
    scene = dp.ParallaxScene(base, depth, amp_x=16, amp_y=4, vignette=0)
    frames = [scene.frame(i / 12.0) for i in range(13)]
    diffs = [float(np.abs(frames[i + 1].astype(int) - frames[i].astype(int)).mean())
             for i in range(12)]
    assert float(np.mean(diffs)) > 0.2, "the clip should actually move"
    assert max(diffs) <= 4.0 * float(np.median(diffs)) + 1.0, f"jump detected: {diffs}"


def test_parallax_scene_has_no_black_border():
    """Edge feather + replicate sampling must never expose black/missing pixels."""
    base, depth = _striped_scene()
    scene = dp.ParallaxScene(base, depth, amp_x=24, amp_y=10, vignette=0)
    fr = scene.frame(1.0)
    band = np.concatenate([fr[0], fr[-1], fr[:, 0], fr[:, -1]])
    assert int(band.min()) > 30, "black/missing pixels found at the frame border"


def test_parallax_scene_render_video_writes_mp4(tmp_path):
    base = _photo(240, 136)
    depth = np.tile(np.linspace(0, 1, 136, dtype=np.float32), (240, 1))
    scene = dp.ParallaxScene(base, depth)
    out = tmp_path / "v.mp4"
    info = scene.render_video(out, 0.2, fps=30)
    assert info["frames"] == 6
    assert out.is_file() and out.stat().st_size > 1000
    leftover = [p.name for p in tmp_path.iterdir() if p.suffix != ".mp4"]
    assert leftover == [], f"unexpected temp files: {leftover}"
