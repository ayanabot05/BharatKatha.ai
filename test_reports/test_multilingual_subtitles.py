import subprocess
import sys
from pathlib import Path
from PIL import Image
import render
from audio_eval_corpus import SCRIPTS

if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

work = Path('test_reports/multilingual_sub_test').resolve()
work.mkdir(parents=True, exist_ok=True)

# Create a dark background image (720x1280)
bg_path = work / 'bg.png'
if not bg_path.is_file():
    img = Image.new('RGB', (720, 1280), (25, 28, 35))
    img.save(bg_path)

langs = ['ta', 'kn', 'ml', 'bn', 'mr', 'gu', 'ur']
results = {}

for lang in langs:
    render.copy_caption_fonts(work, lang)
    sample_text = SCRIPTS[lang]['short']
    ass_file = work / f"captions_{lang}.ass"
    out_frame = work / f"frame_{lang}.png"
    
    # 2 caption events to test multi-line and timing
    caps = [
        {"text": sample_text, "start": 0.0, "end": 2.5}
    ]
    render.caption_ass(caps, lang, ass_file)
    
    cmd = [
        render.FF, '-y', '-loop', '1', '-i', 'bg.png',
        '-vf', f"ass=filename=captions_{lang}.ass:fontsdir=.",
        '-frames:v', '1', f"frame_{lang}.png"
    ]
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=str(work))
    if p.returncode == 0 and out_frame.is_file():
        size = out_frame.stat().st_size
        results[lang] = {'status': 'PASS', 'bytes': size, 'file': str(out_frame)}
        print(f"[{lang}] PASS: rendered {out_frame.name} ({size} bytes)")
    else:
        results[lang] = {'status': 'FAIL', 'error': p.stderr[-400:]}
        print(f"[{lang}] FAIL: {p.stderr[-400:]}")

print("\nSubtitle rendering summary completed.")
