"""Isolated FFmpeg check using previously generated Telugu Piper audio."""
import json
import sys
import time
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
import render
from audio_eval_corpus import SCRIPTS

work = Path(__file__).resolve().parent
audio = ROOT / "test_reports" / "piper-audio-te-2026-10-15" / "te_short.mp3"
if not audio.is_file():
    raise SystemExit(f"Missing real Piper audio: {audio}")
image = work / "fixture.jpg"
clip = work / "captioned-clip.mp4"
video = work / "isolated-render.mp4"
subtitles = work / "isolated-render.srt"
Image.new("RGB", (1440, 2560), (44, 99, 83)).save(image, quality=90)
duration = render.duration(audio)
caps = render.checked_captions(render.chunk_captions(SCRIPTS["te"]["short"], duration), duration)
subtitles.write_text(render.srt(caps), encoding="utf-8")
started = time.monotonic()
render.scene_clip(image, duration, caps, "te", clip, 0, work)
clip_seconds = time.monotonic() - started
started = time.monotonic()
render.mux([clip], audio, video, work)
mux_seconds = time.monotonic() - started
render.run(["-i", str(video), "-f", "null", "NUL"])
report = {
    "scope": "isolated_ffmpeg_only_not_studio_project",
    "source_audio": str(audio),
    "source_audio_seconds": duration,
    "caption_timing": "estimated",
    "caption_count": len(caps),
    "caption_clip_seconds": round(clip_seconds, 3),
    "mux_seconds": round(mux_seconds, 3),
    "mp4_path": str(video),
    "mp4_bytes": video.stat().st_size,
    "mp4_duration_seconds": render.duration(video),
    "srt_path": str(subtitles),
    "decode": "PASS",
}
(work / "render_probe.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))
