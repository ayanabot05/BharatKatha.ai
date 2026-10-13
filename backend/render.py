"""FFmpeg composer: scene images + Ken Burns motion + narration + burned-in captions -> 720x1280 MP4."""
import re
import io
import shutil
import subprocess
import tempfile
import math
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont, ImageOps

FF = imageio_ffmpeg.get_ffmpeg_exe()
W, H, FPS = 720, 1280, 30
FONTS = Path(__file__).parent / "fonts"
FONT_BY_LANG = {"te": "NotoSansTelugu.ttf", "hi": "NotoSansDevanagari.ttf", "mr": "NotoSansDevanagari.ttf",
                "ta": "NotoSansTamil.ttf", "bn": "NotoSansBengali.ttf", "gu": "NotoSansGujarati.ttf",
                "kn": "NotoSansKannada.ttf", "ml": "NotoSansMalayalam.ttf", "or": "NotoSansOriya.ttf",
                "ur": "NotoSansArabic.ttf", "en": "NotoSans-Regular.ttf"}


def copy_caption_fonts(work, lang):
    for filename in {FONT_BY_LANG.get(lang, FONT_BY_LANG["en"]), "NotoSans-Regular.ttf"}:
        shutil.copyfile(FONTS / filename, Path(work) / filename)


def font_family(lang):
    filename = FONT_BY_LANG.get(lang, FONT_BY_LANG["en"])
    return filename.replace(".ttf", "").replace("-Regular", "").replace("NotoSans", "Noto Sans ").strip()


def run(cmd, cwd=None):
    p = subprocess.run([FF, "-y", "-hide_banner", "-loglevel", "error", *cmd], capture_output=True, text=True, cwd=cwd)
    if p.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {p.stderr[-600:]}")


def duration(path) -> float:
    err = subprocess.run([FF, "-hide_banner", "-i", str(path)], capture_output=True, text=True).stderr
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", err)
    return int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3]) if m else 0.0


def duration_bytes(data: bytes) -> float:
    err = subprocess.run([FF, "-hide_banner", "-i", "pipe:0", "-f", "null", "-"], input=data, capture_output=True).stderr.decode(errors="ignore")
    m = re.findall(r"time=(\d+):(\d+):([\d.]+)", err)
    return int(m[-1][0]) * 3600 + int(m[-1][1]) * 60 + float(m[-1][2]) if m else 0.0


def to_mp3_bytes(data: bytes) -> bytes:
    p = subprocess.run([FF, "-hide_banner", "-loglevel", "error", "-i", "pipe:0", "-ac", "1", "-ar", "44100", "-b:a", "128k", "-f", "mp3", "pipe:1"],
                       input=data, capture_output=True)
    if p.returncode != 0 or not p.stdout:
        raise RuntimeError("ffmpeg could not decode audio")
    return p.stdout


def concat_audio(files, dst):
    lst = Path(dst).with_suffix(".txt")
    lst.write_text("".join(f"file '{f}'\n" for f in files))
    run(["-f", "concat", "-safe", "0", "-i", str(lst), "-ac", "1", "-ar", "44100", "-b:a", "128k", str(dst)])


def pad_audio(src, dst, target_seconds):
    """Add a brief silent tail without changing the spoken words or their timing."""
    run(["-i", str(src), "-af", "apad", "-t", f"{target_seconds:.2f}",
         "-ac", "1", "-ar", "44100", "-b:a", "128k", str(dst)])


def prep_image(src, dst):
    ImageOps.fit(Image.open(src).convert("RGB"), (W * 2, H * 2), Image.LANCZOS).save(dst, quality=92)


def caption_png(text, lang, dst):
    font = ImageFont.truetype(str(FONTS / FONT_BY_LANG.get(lang, FONT_BY_LANG["te"])), 44, layout_engine=ImageFont.Layout.RAQM)
    probe = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    lines, cur = [], ""
    for w in text.split():
        t = f"{cur} {w}".strip()
        if probe.textlength(t, font=font) > W - 120 and cur:
            lines.append(cur)
            cur = w
        else:
            cur = t
    lines.append(cur)
    lh = 64
    img = Image.new("RGBA", (W, lh * len(lines) + 36), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    widest = max(probe.textlength(line, font=font) for line in lines)
    x0 = (W - widest) / 2 - 24
    d.rounded_rectangle([x0, 0, W - x0, img.height], radius=22, fill=(15, 23, 42, 170))
    for i, line in enumerate(lines):
        lw = probe.textlength(line, font=font)
        d.text(((W - lw) / 2, 14 + i * lh), line, font=font, fill=(255, 255, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0, 255))
    img.save(dst)


def thumbnail_png(src, title, lang):
    """Return a vertical cover image using an approved scene picture."""
    img = ImageOps.fit(Image.open(src).convert("RGB"), (W, H), Image.LANCZOS).convert("RGBA")
    shade = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shade)
    for y in range(H):
        alpha = int(215 * max(0, 1 - y / 570))
        sd.line([(0, y), (W, y)], fill=(4, 8, 20, alpha))
    img = Image.alpha_composite(img, shade)
    temp_root = Path(__file__).parent / "media_cache"
    temp_root.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=temp_root) as tmp:
        work = Path(tmp)
        img.convert("RGB").save(work / "cover.png", format="PNG")
        copy_caption_fonts(work, lang)
        caption_ass([{"text": title, "start": 0, "end": 1}], lang, work / "title.ass", placement="top")
        run(["-i", "cover.png", "-vf", "ass=filename=title.ass:fontsdir=.", "-frames:v", "1",
             "-update", "1", "cover_final.png"], cwd=work)
        return (work / "cover_final.png").read_bytes()


def chunk_captions(text, dur, offset=0.0, words_per=4):
    words = text.split()
    chunks = [" ".join(words[i:i + words_per]) for i in range(0, len(words), words_per)] or [""]
    total = sum(len(c) for c in chunks) or 1
    out, t = [], offset
    for c in chunks:
        d = dur * len(c) / total
        out.append({"text": c, "start": round(t, 2), "end": round(t + d, 2)})
        t += d
    return out


def checked_captions(caps, duration, allow_points=False):
    """Reject unusable timing instead of silently burning misleading subtitles."""
    if not isinstance(caps, list) or not caps:
        raise ValueError("No timed captions were returned")
    result, previous = [], 0.0
    for cap in caps:
        if not isinstance(cap, dict) or not isinstance(cap.get("text"), str) or not cap["text"].strip():
            raise ValueError("Caption text is missing")
        start, end = float(cap["start"]), float(cap["end"])
        if not math.isfinite(start) or not math.isfinite(end) or start < 0 or end < start or (end == start and not allow_points):
            raise ValueError("Caption timing is invalid")
        if start < previous - 0.01 or start >= duration or end > duration + 0.25:
            raise ValueError("Caption timing overlaps or exceeds the audio")
        start, end = max(start, previous), min(end, duration)
        if end < start or (end == start and not allow_points):
            raise ValueError("Caption has no playable duration")
        result.append({"text": cap["text"].strip(), "start": start, "end": end})
        previous = end
    return result


def timed_captions(words, duration, words_per=4):
    """Group provider word boundaries; preserve pauses rather than guessing from text length."""
    # Some voices emit a word onset with zero duration. It is usable inside a
    # phrase whose final word has a measured end; it is not a valid subtitle alone.
    words = checked_captions(words, duration, allow_points=True)
    caps, group = [], []
    for word in words:
        if group and (len(group) >= words_per or word["start"] - group[-1]["end"] > 0.5):
            caps.append({"text": " ".join(w["text"] for w in group),
                         "start": group[0]["start"], "end": group[-1]["end"]})
            group = []
        group.append(word)
    if group:
        caps.append({"text": " ".join(w["text"] for w in group),
                     "start": group[0]["start"], "end": group[-1]["end"]})
    return checked_captions(caps, duration)


def frame_durations(durations):
    """Round cumulative cuts so per-scene rounding cannot accumulate AV drift."""
    result, total, previous = [], 0.0, 0
    for value in durations:
        if not math.isfinite(value) or value <= 0:
            raise ValueError("Every scene needs a positive measured duration")
        total += value
        end = math.ceil(total * FPS - 1e-8)
        if end <= previous:
            raise ValueError("A scene is shorter than one video frame")
        result.append((end - previous) / FPS)
        previous = end
    return result


def _ass_time(seconds):
    centis = max(0, round(seconds * 100))
    return f"{centis // 360000:01}:{centis // 6000 % 60:02}:{centis // 100 % 60:02}.{centis % 100:02}"


SCRIPT_FONT_CONFIG = {
    "te": {"size": 42, "margin": 310},
    "kn": {"size": 42, "margin": 310},
    "ml": {"size": 42, "margin": 310},
    "ta": {"size": 44, "margin": 310},
    "hi": {"size": 46, "margin": 320},
    "mr": {"size": 46, "margin": 320},
    "bn": {"size": 46, "margin": 320},
    "gu": {"size": 46, "margin": 320},
    "or": {"size": 44, "margin": 310},
    "ur": {"size": 48, "margin": 310},
    "en": {"size": 48, "margin": 320},
}


def caption_ass(caps, lang, dst, placement="bottom"):
    family = font_family(lang)
    cfg = SCRIPT_FONT_CONFIG.get(lang, {"size": 46, "margin": 320})
    if placement == "top":
        alignment, margin, size = 8, 80, round(cfg["size"] * 1.5)
    else:
        # Keep subtitles below the center action area while clearing platform controls.
        alignment, margin, size = 2, 140, cfg["size"]
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{family},{size},&H00FFFFFF,&H00FFFFFF,&H00000000,&H990F172A,0,0,0,0,100,100,0,0,3,2,0,{alignment},48,48,{margin},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for c in caps:
        value = str(c["text"]).replace("{", "(").replace("}", ")")
        if lang != "en":
            # Explicitly select the bundled Latin face: system fallback differs
            # across DirectWrite/fontconfig and may be absent in the container.
            value = re.sub(r"[A-Za-z0-9₹%]+", lambda m: "{\\fnNoto Sans\\fs" + str(round(size * .75)) + "}" + m[0] + "{\\r}", value)
        value = value.replace("\n", "\\N")
        events.append(f"Dialogue: 0,{_ass_time(c['start'])},{_ass_time(c['end'])},Default,,0,0,0,,{value}")
    Path(dst).write_text(header + "\n".join(events) + "\n", encoding="utf-8")


def camera_motion(idx: int, frames: int):
    """
    Cinematic camera movement per scene beat:
    - 0 (Hook): Energetic push-in for immediate thumb-stopping curiosity.
    - 1 (Setup): Smooth left-to-right pan establishing environment.
    - 2 (Conflict): Smooth pull-out / reveal.
    - 3 (Action): Smooth right-to-left pan focusing on movement.
    - 4+ (Climax/Ending): Alternating push-in and gentle settle.
    """
    if idx == 0:
        step = 0.18 / frames
        return f"min(1.0+{step:.6f}*on,1.18)", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    mode = idx % 4
    if mode == 1:
        return "1.10", f"(iw-iw/zoom)*(on/{frames})", "ih/2-(ih/zoom/2)"
    elif mode == 2:
        step = 0.14 / frames
        return f"max(1.14-{step:.6f}*on,1.0)", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    elif mode == 3:
        return "1.10", f"(iw-iw/zoom)*(1-on/{frames})", "ih/2-(ih/zoom/2)"
    else:
        step = 0.12 / frames
        return f"min(1.0+{step:.6f}*on,1.12)", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"


def scene_clip(img, dur, caps, lang, out, idx, work: Path):
    frames = max(round(dur * FPS), 1)
    z, x, y = camera_motion(idx, frames)
    inputs = ["-i", str(img)]
    graph = [f"[0:v]zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s={W}x{H}:fps={FPS}[v0]"]
    last = "v0"
    if caps:
        copy_caption_fonts(work, lang)
        ass_name = f"captions_{idx}.ass"
        caption_ass(caps, lang, work / ass_name)
        graph.append(f"[{last}]ass=filename={ass_name}:fontsdir=.[v1]")
        last = "v1"
    run([*inputs, "-filter_complex", ";".join(graph), "-map", f"[{last}]", "-t", f"{dur:.2f}",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p", "-r", str(FPS), str(out)], cwd=work)


def mux(clips, audio, out, work: Path, bgm: Path = None):
    lst = work / "clips.txt"
    lst.write_text("".join(f"file '{c}'\n" for c in clips))
    if bgm and Path(bgm).is_file():
        # Mix narration (1.0) with background music auto-ducked (-16dB = 0.15 volume)
        run(["-f", "concat", "-safe", "0", "-i", str(lst), "-i", str(audio), "-i", str(bgm),
             "-filter_complex", "[1:a]volume=1.0[voice];[2:a]volume=0.15[bg];[voice][bg]amix=inputs=2:duration=first:dropout_transition=2[aout]",
             "-map", "0:v", "-map", "[aout]", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
             "-shortest", "-movflags", "+faststart", str(out)])
    else:
        run(["-f", "concat", "-safe", "0", "-i", str(lst), "-i", str(audio), "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
             "-shortest", "-movflags", "+faststart", str(out)])


def srt(caps):
    def ts(s):
        ms = int(round(s * 1000))
        return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"
    return "\n".join(f"{i + 1}\n{ts(c['start'])} --> {ts(c['end'])}\n{c['text']}\n" for i, c in enumerate(caps))
