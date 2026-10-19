import asyncio
import json
import sys
from pathlib import Path
from audio_eval_corpus import SCRIPTS
import ai
import render

# Fix stdout encoding on Windows
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

async def test_all():
    langs = ['ta', 'kn', 'ml', 'bn', 'mr', 'gu', 'ur']
    results = {}
    for lang in langs:
        text = SCRIPTS[lang]['short']
        try:
            res = await ai._edge_speech(text, 'fable', 1.0, language=lang)
            dur = render.duration_bytes(res['audio'])
            words = res['words']
            first_w = words[0] if words else None
            last_w = words[-1] if words else None
            
            # Check timing monotonic and valid
            is_monotonic = True
            for i in range(len(words) - 1):
                if words[i]['start'] > words[i+1]['start'] or words[i]['end'] > words[i+1]['end']:
                    is_monotonic = False
                    break
            
            results[lang] = {
                'status': 'OK',
                'audio_bytes': len(res['audio']),
                'duration': dur,
                'word_count': len(words),
                'words': words,
                'is_monotonic': is_monotonic,
                'last_word_end': last_w['end'] if last_w else 0,
                'audio_dur_diff': abs(dur - (last_w['end'] if last_w else 0))
            }
            print(f"[{lang}] SUCCESS: audio={len(res['audio'])} bytes, dur={dur:.2f}s, words={len(words)}, monotonic={is_monotonic}")
        except Exception as e:
            results[lang] = {'status': 'ERROR', 'error': str(e)}
            print(f"[{lang}] ERROR: {e}")
    
    out_file = Path('test_reports/probe_7_languages_result.json')
    out_file.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f"Saved results to {out_file}")

if __name__ == '__main__':
    asyncio.run(test_all())
