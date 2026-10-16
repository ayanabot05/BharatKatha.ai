# Real Telugu Piper CPU probe — 15 October 2026

## Scope and provenance

This is a bounded local inference run through the application's Piper HTTP adapter and `backend/benchmark_piper_audio.py`. It is not a deployed creator journey or a native-speaker quality acceptance test. The Windows 11 laptop used an Intel Core i5-10210U CPU with eight logical processors. RAM usage was not measured. No cloud instance or premium speech endpoint was invoked.

The isolated Piper 1.8.0 and ONNX Runtime 1.31.0 installation is in ignored `backend/.piper-eval/`. The voice files are in ignored `backend/.piper-models/`. The model was `te_IN-padmavathi-medium`; the ONNX SHA-256 was `414AA5960D91CEB6E45BBDF8C27FDC71AF09F205130D7BE4E99470F3C2CFA57D`, matching the publisher's [Git LFS pointer](https://huggingface.co/rhasspy/piper-voices/commit/9f515967e4dea537165e923057c7c128e394fb7b). The [voice model card commit](https://huggingface.co/rhasspy/piper-voices/commit/ff43c1e79f98a765202dcfb03710851f9ec4ff2e) identifies its IndicVoices-R training dataset as CC BY 4.0. [Piper 1.8.0](https://pypi.org/project/piper-tts/) is GPL-3.0-or-later. These terms allow a commercial-use candidate, subject to required attribution and any source-distribution obligations. Production deployment needs a final rights and notice review; the operator's `verified-commercial` manifest value records the preliminary terms check, not completed legal sign-off.

## Procedure

The Piper server listened on `127.0.0.1:5008`; `/info` returned the Telugu voice. `PIPER_VOICES_JSON` mapped `te` to this localhost endpoint and exact hash revision. The script ran the fixed short, names/numbers, and dialogue inputs from `backend/benchmark_piper_audio.py` and wrote MP3s and `te_report.json` to ignored `test_reports/piper-audio-te-2026-10-15/`. The server was stopped after the probe. No request was routed to Chirp or OpenAI.

| Case | Audio duration | Wall time | MP3 bytes | Signal check |
| --- | ---: | ---: | ---: | --- |
| Short | 3.47 s | 3.300 s | 55,632 | Decoded; RMS 0.20435 |
| Names and numbers | 10.32 s | 1.288 s | 165,137 | Decoded; RMS 0.15472 |
| Dialogue | 5.96 s | 0.779 s | 95,338 | Decoded; RMS 0.18438 |

FFmpeg decoded all three outputs. Measured peaks were approximately 0.94–0.96. The first request includes warm-up, so these measurements must not be extrapolated to a full video or server concurrency. MP3 duration and latency are recorded by the harness; caption timing is estimated. The JSON report leaves estimated and actual infrastructure cost null because no billing measurement exists. Incremental paid API/cloud usage was zero; local electricity was not metered.

## Acceptance gaps

- A fluent Telugu speaker must score pronunciation, names and numbers, naturalness, emotion, and dialogue. Signal-level checks cannot answer these questions.
- Run an application project from narration selection through render/download with this service. The probe tested the adapter path, not the full production journey.
- Establish a commercially suitable inference route and run the same three scripts for all ten remaining app languages. Telugu, Hindi, Tamil and Marathi form the first complete acceptance cohort. The examined Hindi `pratham` voice cites a noncommercial dataset and must not be enabled for commercial use. See the [11-language execution checkpoint](AUDIO_11_LANGUAGE_EXECUTION_2026-10-15.md).
- Measure hardware RAM and concurrent throughput. Review exact voice attribution and Piper GPL notice/source obligations before production packaging.
- Compare with Chirp only after an explicit premium budget and run scope are approved.
