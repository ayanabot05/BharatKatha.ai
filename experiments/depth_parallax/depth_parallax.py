"""Experimental 2.5D depth-parallax renderer (CPU + FFmpeg).

This is genuine depth-based parallax, not a Ken Burns zoom/pan.

For every output frame we build a per-pixel coordinate field. Each pixel is
displaced sideways by an amount proportional to its estimated depth minus a
pivot depth. Near surfaces therefore move one way and far surfaces the other
way about the pivot, which is the defining cue of 2.5D parallax. A slow zoom
is layered on top for a cinematic dolly feel.

Guarantees that keep it production-safe:
  * Output resolution/aspect match the current engine (720x1280, 9:16, 30 fps).
  * A radial edge feather ramps displacement to zero at the frame border, so
    the remap never samples outside the image and cannot expose torn edges.
  * Frames are piped straight to FFmpeg; no intermediate files are left behind.

No paid API is used. No network access. No production module is modified.
"""
from __future__ import annotations

import os
import subprocess

import cv2
import numpy as np

W, H, FPS = 720, 1280, 30


def _smoothstep(x: np.ndarray | float):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)


def edge_feather(shape, frac: float = 0.07) -> np.ndarray:
    """1.0 in the interior, ramping smoothly to 0.0 within ``frac`` of each border."""
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


def edge_damp(depth: np.ndarray, k: float = 3.0) -> np.ndarray:
    """Down-weight displacement where depth changes sharply.

    At a depth discontinuity (a person against a wall, a pillar against a
    courtyard) a lateral shift tears the silhouette. Damping displacement by
    the depth-gradient magnitude keeps such structures intact while preserving
    the global near/far parallax.
    """
    d = np.asarray(depth, np.float32)
    gx = cv2.Sobel(d, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(d, cv2.CV_32F, 0, 1, ksize=3)
    mag = cv2.magnitude(gx, gy)
    return (1.0 / (1.0 + k * mag)).astype(np.float32)


def fit_cover_bgr(path, w: int = W, h: int = H) -> np.ndarray:
    """Aspect-preserving centre crop to w x h, matching the production framing."""
    from PIL import Image, ImageOps

    im = ImageOps.fit(Image.open(path).convert("RGB"), (w, h), Image.LANCZOS)
    return cv2.cvtColor(np.array(im), cv2.COLOR_RGB2BGR)


def frame_at(base, depth, t, *, amp_x=12.0, amp_y=4.0, zoom=0.09,
             feather=0.07, vig=None, pivot=None, **kw) -> np.ndarray:
    """Render a single parallax frame at normalised time ``t`` in [0, 1]."""
    h, w = base.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    return frame_from_grids(base, depth, xx, yy, t,
                            amp_x=amp_x, amp_y=amp_y, zoom=zoom,
                            feather=feather, vig=vig, pivot=pivot, **kw)


def frame_from_grids(base, depth, xx, yy, t, *, amp_x=12.0, amp_y=4.0,
                     zoom=0.09, feather=0.07, vig=None, pivot=None,
                     damp=None, breath=0.012) -> np.ndarray:
    h, w = base.shape[:2]
    if depth is None:
        raise ValueError("frame_from_grids: a depth map is required")
    depth = np.asarray(depth, np.float32)
    if depth.shape[:2] != (h, w):
        depth = cv2.resize(depth, (w, h), interpolation=cv2.INTER_LINEAR)
    if pivot is None:
        pivot = float(np.median(depth))

    e = float(_smoothstep(np.array(t, np.float32)))
    lateral = e * 2.0 - 1.0          # -1 .. +1 camera dolly sweep
    z = 1.0 + zoom * e               # slow push-in

    cx, cy = (w - 1) / 2.0, (h - 1) / 2.0
    xc = cx + (xx - cx) / z
    yc = cy + (yy - cy) / z

    d_cam = cv2.remap(depth, xc, yc, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    disp = d_cam - pivot
    if damp is not None:
        disp = disp * damp
    fe = edge_feather((h, w), feather)
    xs = xc + amp_x * lateral * disp * fe
    ys = yc + amp_y * lateral * disp * fe

    out = cv2.remap(base, xs, ys, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    gain = (1.0 + breath * np.sin(2.0 * np.pi * t))
    if vig is not None:
        out = out.astype(np.float32) * vig[..., None]
    else:
        out = out.astype(np.float32)
    return np.clip(out * gain, 0, 255).astype(np.uint8)


def render_parallax(image, depth, out_path, duration, *, fps: int = FPS, **kw) -> str:
    """Write a depth-parallax MP4 (H.264, yuv420p) of ``duration`` seconds.

    ``image`` is a path or a BGR array; ``depth`` is a float32 [0,1] map.
    Frames are streamed to FFmpeg over stdin; nothing is written to disk
    except ``out_path``.
    """
    import imageio_ffmpeg

    if depth is None:
        raise ValueError("render_parallax: a depth map is required")
    base = image if isinstance(image, np.ndarray) else fit_cover_bgr(image)
    h, w = base.shape[:2]
    vig_strength = kw.pop("vignette", 0.14)
    vig = vignette_mask(h, w, vig_strength) if vig_strength else None
    if not isinstance(depth, np.ndarray) or depth.shape[:2] != (h, w):
        depth = cv2.resize(np.asarray(depth, np.float32), (w, h), interpolation=cv2.INTER_LINEAR)
    damp_k = kw.pop("edge_damp", 3.0)
    damp = edge_damp(depth, damp_k) if damp_k else None

    n = max(int(round(duration * fps)), 1)
    ff = os.environ.get("FFMPEG_BINARY") or imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [
        ff, "-y", "-hide_banner", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{w}x{h}", "-r", str(fps), "-i", "pipe:0",
        "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-pix_fmt", "yuv420p", "-r", str(fps), str(out_path),
    ]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    try:
        for i in range(n):
            fr = frame_from_grids(base, depth, xx, yy, i / max(n - 1, 1), vig=vig, damp=damp, **kw)
            proc.stdin.write(fr.tobytes())
    finally:
        if proc.stdin:
            proc.stdin.close()
        code = proc.wait()
    if code != 0:
        raise RuntimeError(f"render_parallax: ffmpeg exited with {code}")
    return str(out_path)


def adaptive_strength(depth, lo: float = 0.10, hi: float = 0.22, floor: float = 0.6) -> float:
    """Recommended animation-strength multiplier for a scene's depth map.

    Low-contrast (flat / single-plane) depth has little to separate, so pushing
    it hard only adds artifacts. Scale amplitude down for those scenes and keep
    full strength for scenes with clear depth structure.
    """
    d = np.asarray(depth, np.float32)
    if d.size == 0:
        return floor
    c = float(np.std(d))
    s = (c - lo) / max(hi - lo, 1e-6)
    return float(np.clip(floor + (1.0 - floor) * s, floor, 1.0))


class ParallaxScene:
    """Precompute the static parts of the parallax field once per scene.

    ``fast=True`` skips the per-frame depth remap (it samples depth on the static
    grid instead). With the small zoom used here the visual difference is tiny,
    but it removes one full-frame remap per frame.
    """

    def __init__(self, base, depth, *, amp_x=12.0, amp_y=4.0, zoom=0.09,
                 feather=0.07, damp_k=6.0, vignette=0.14, breath=0.012,
                 pivot=None, strength=1.0, fast=False):
        if depth is None:
            raise ValueError("ParallaxScene: a depth map is required")
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
        self.disp_static = ((self.depth - self.pivot) * self.damp).astype(np.float32)
        # Precompute everything that does not depend on time.
        self.dispfe_x = (self.amp_x * self.disp_static * self.fe).astype(np.float32)
        self.dispfe_y = (self.amp_y * self.disp_static * self.fe).astype(np.float32)

    def displacement_px(self, t: float = 1.0) -> np.ndarray:
        """Horizontal displacement magnitude in pixels at time ``t``."""
        e = float(_smoothstep(np.array(t, np.float32)))
        return np.abs((e * 2.0 - 1.0) * self.dispfe_x)

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

    def render_video(self, out_path, duration, *, fps: int = FPS, crf: int = 20,
                     preset: str = "veryfast", progress=None) -> dict:
        """Write an H.264 MP4 of ``duration`` seconds, streaming frames to FFmpeg.

        Returns timing info (frame count, frame-generation seconds, ms/frame).
        Only ``out_path`` is written; no intermediate files.
        """
        import time
        import imageio_ffmpeg

        n = max(int(round(duration * fps)), 1)
        ff = os.environ.get("FFMPEG_BINARY") or imageio_ffmpeg.get_ffmpeg_exe()
        cmd = [
            ff, "-y", "-hide_banner", "-loglevel", "error",
            "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{self.w}x{self.h}",
            "-r", str(fps), "-i", "pipe:0", "-an",
            "-c:v", "libx264", "-preset", preset, "-crf", str(crf),
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-r", str(fps), str(out_path),
        ]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        gen = 0.0
        try:
            for i in range(n):
                t0 = time.perf_counter()
                fr = self.frame(i / max(n - 1, 1))
                gen += time.perf_counter() - t0
                proc.stdin.write(fr.tobytes())
                if progress is not None:
                    progress(i + 1, n)
        finally:
            if proc.stdin:
                proc.stdin.close()
            code = proc.wait()
        if code != 0:
            raise RuntimeError(f"ParallaxScene.render_video: ffmpeg exited with {code}")
        return {"frames": n, "frame_gen_seconds": round(gen, 3),
                "ms_per_frame": round(gen / n * 1000.0, 1)}

    def out_of_bounds(self, t: float = 1.0) -> int:
        """Pixels that would sample outside the image before clamping (should be 0)."""
        e = float(_smoothstep(np.array(t, np.float32)))
        lateral = e * 2.0 - 1.0
        iz = 1.0 / (1.0 + self.zoom * e)
        xc = self.cx + self.xoff * iz
        yc = self.cy + self.yoff * iz
        xs = xc + lateral * self.dispfe_x
        ys = yc + lateral * self.dispfe_y
        bad = (xs < 0) | (xs > self.w - 1) | (ys < 0) | (ys > self.h - 1)
        return int(bad.sum())
