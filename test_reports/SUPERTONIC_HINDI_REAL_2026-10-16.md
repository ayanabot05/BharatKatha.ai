# Hindi local open-model execution — 16 October 2026

## Model and license

- The official Piper Hindi `pratham` and `priyamvada` voice cards cite CC BY-NC-SA 4.0 datasets. `rohan` is derived from English `lessac`, whose source dataset excludes commercial use. None was configured as commercially cleared.
- Selected model: [archived official Supertonic 3 weights](https://huggingface.co/supertone-oss-archive/supertonic-3), revision `aafc6e32416a594460b32413efc49d7fe4ce6d46`, bundled M1 voice style. The [model license](https://huggingface.co/supertone-oss-archive/supertonic-3/blob/main/LICENSE) is OpenRAIL-M, with commercial deployment rights and use restrictions, including intelligible AI-output disclosure. The [Python SDK](https://github.com/supertone-oss-archive/supertonic-py/blob/main/LICENSE) is MIT; its code license does not replace the weight license. The model card does not provide a separate M1 voice license or detailed training-data provenance.
- Local pinned model download: 398,667,957 bytes of selected ONNX/config/M1/license files; no GPU, cloud inference or paid speech call. The app loads the model only from `SUPERTONIC_HINDI_MODEL_DIR`, checks the reviewed LICENSE hash and pinned revision, and never downloads at request time.

## Three real Hindi probes

All MP3s are local ignored evidence under `test_reports/supertonic-hindi-2026-10-16/`; see `report.json` there for exact text, SHA-256, CPU time, cold model-load time and encoded-file integrity.

| Case | MP3 | CPU inference wall time | MP3 duration | Size | Peak process RSS |
| --- | --- | ---: | ---: | ---: | ---: |
| Short | [hi_short_supertonic3_M1.mp3](supertonic-hindi-2026-10-16/hi_short_supertonic3_M1.mp3) | 2.814 s | 3.413 s | 39,939 B | 481.9 MiB |
| Names/numbers | [hi_names_numbers_supertonic3_M1.mp3](supertonic-hindi-2026-10-16/hi_names_numbers_supertonic3_M1.mp3) | 2.858 s | 7.523 s | 98,120 B | 497.7 MiB |
| Dialogue | [hi_dialogue_supertonic3_M1.mp3](supertonic-hindi-2026-10-16/hi_dialogue_supertonic3_M1.mp3) | 1.789 s | 3.971 s | 47,446 B | 499.2 MiB |

Cold model load took 2.503 s and peaked at 462.2 MiB process RSS. The run used four ONNX intra-op threads on an eight-logical-CPU Windows machine. Every MP3 was decoded and checked for finite non-silent samples. These three latency values are observations, not a general speed SLA.

## Local Studio journey

A separate Hindi project `43ae08193d8e4659aece55d6f3fa2001` reused five real, previously approved visual assets from the Telugu water-pipe story. Its Hindi text and approval fingerprint were seeded solely as a local audio workflow fixture; no paid script/image generation or claim of Hindi editorial approval is implied. The Telugu project and its route were untouched.

| Stage | Result and evidence |
| --- | --- |
| Browser preview | **PASS** — Studio showed Supertonic 3 M1 and `POST /api/voice/preview` returned HTTP 200. |
| Narration save | **PASS** — `POST /api/projects/<id>/audio/ai` returned HTTP 200; saved `provider=supertonic`, all five scene model IDs pinned to the revision, and a 373,698-byte 23.33 s MP3. Browser audio player entered `pause` state after playback began. |
| Captions | **PASS for estimated timing** — Studio displayed the estimated-caption warning on Audio and Render. The export has 16 SRT entries. Human synchronization review is **NOT TESTED**. |
| Render and playback | **PASS** — five images produced a 3,171,862-byte, 23.3 s MP4. FFmpeg decoded it completely. Browser video had `readyState=4`, `paused=false`, and no media error. A 2 s frame visibly contains the `AI-generated narration` label and Hindi captions. |
| Narration identity | **PASS** — decoded MP4 audio versus saved Supertonic narration has correlation `0.999942`. |
| Browser download | **PASS** — the Studio MP4 link saved `e991bd241ea7448fad8177d728516a2e.mp4` in Downloads. `?download=1` returned an attachment header; inline media GET did not. The preserved copy is [hindi_studio_final.mp4](supertonic-hindi-2026-10-16/hindi_studio_final.mp4). |
| Cost | **PASS for no paid inference** — local CPU only, premium-rate manifest empty, explicit project provider `supertonic`. Electricity was not metered. |

Founder listening feedback was “hindi was good.” No case-by-case fluent-speaker rubric, word-error audit, or human caption synchronization verdict was supplied, so the quality gate remains open. The full Studio flow passed locally; hosted deployment is **NOT TESTED**. Additional status fields and file hashes are in `studio_result.json` in the ignored evidence directory.

Focused backend regression: 14 tests passed (`test_supertonic_tts.py` plus Piper suite). Frontend production build passed. The first backend test run inside the sandbox stalled on Windows async test setup and was interrupted; the run outside the sandbox passed.
