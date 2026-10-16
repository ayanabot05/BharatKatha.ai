# Audio coverage across the app's languages — 16 October 2026

The app offers 11 creation languages. The same three-case smoke corpus now exists for every one in `backend/audio_eval_corpus.py`: short narration, names/numbers, and dialogue. Text translations are provisional until fluent speakers check them. Run `python backend/audio_coverage.py` from the repository root to inspect evidence from local report files. The command never calls a model or paid service.

The [execution checkpoint](../test_reports/AUDIO_11_LANGUAGE_EXECUTION_2026-10-15.md) records the required sample paths, actual inference times and pipeline statuses for every language. Telugu and Hindi now have real local audio and Studio MP4 exports; the other nine have no real open-model audio evidence.

The founder's requested completion targets are **100% for Telugu, Hindi, Tamil and Marathi** and **90% for the other offered languages**. These are priorities for work, not achieved quality scores. A scored native-speaker rubric and a larger benchmark set are required before a quality percentage can be reported. All languages follow the same sequence: reviewed text → licensed model and compute → real audio → fluent-speaker assessment → application project and export. Do not promote the primary group as a cohort until all four reach the same evidence gate.

| Language | Priority | Smoke corpus | Real open-model audio | Native review | Full app/export |
| --- | --- | --- | --- | --- | --- |
| Telugu (`te`) | 100% target | Ready | Three local Piper samples plus saved project narration | Pending | Controlled Studio preview, save, caption warning, MP4 playback and browser download passed; human sync review pending |
| Hindi (`hi`) | 100% target | Ready | Three local Supertonic 3 M1 MP3s, 1.789–2.858 s inference, 499.2 MiB peak process RSS | Founder listening feedback favorable; detailed fluent review pending | Local preview, save, estimated captions, MP4 playback and browser download passed; human sync review pending |
| Tamil (`ta`) | 100% target | Ready | Pending | Pending | Pending |
| Marathi (`mr`) | 100% target | Ready | Pending | Pending | Pending |
| Bengali (`bn`) | 90% target | Ready | Pending | Pending | Pending |
| Gujarati (`gu`) | 90% target | Ready | Pending | Pending | Pending |
| Urdu (`ur`) | 90% target | Ready | Pending | Pending | Pending |
| Kannada (`kn`) | 90% target | Ready | Pending | Pending | Pending |
| Odia (`or`) | 90% target | Ready | Pending | Pending | Pending |
| Malayalam (`ml`) | 90% target | Ready | Pending | Pending | Pending |
| English (`en`) | 90% target | Ready | Pending | Pending | Pending |

## Model coverage and restrictions

| Candidate | Coverage of app languages | Current constraint |
| --- | --- | --- |
| [Indic Parler-TTS](https://huggingface.co/ai4bharat/indic-parler-tts) | Its model card lists all 11 offered languages and an Apache 2.0 model license | Weight access is gated. The listed model is large; GPU/runtime, dataset rights, per-language quality and cost need verification before enabling it. No local or cloud inference run has occurred. |
| [IndicF5](https://huggingface.co/ai4bharat/IndicF5) | Nine offered Indian languages; its card excludes Urdu and English | Gated weights; synthesis requires reference audio and its transcript with explicit voice permission. It cannot be the sole route for all 11. |
| [Indic-Speak](https://huggingface.co/bodhan-ai/indic-speak) | Its card labels all 11 offered languages as production tier | Gated access; its license asks for permission before hosting it for others. Do not enable a hosted product route without that permission. Publisher quality claims are not our measured results. |
| [Piper voice catalog](https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/VOICES.md) | The listed voices include Telugu, Hindi and Malayalam plus English, but no Tamil or Marathi | Per-voice rights differ. The Telugu `padmavathi` candidate produced real CPU output; examined Hindi voices and English lessac lineage have noncommercial or research-only concerns. Piper alone cannot serve the four priority languages. |
| [Supertonic 3](https://huggingface.co/supertone-oss-archive/supertonic-3) | Hindi is the only supported language among the app's ten Indian languages; English is also supported | Pinned M1 local CPU Hindi inference and Studio export passed. Weights and bundled voice style use [OpenRAIL-M](https://huggingface.co/supertone-oss-archive/supertonic-3/blob/main/LICENSE), with commercial use conditioned on restrictions and intelligible AI-output disclosure. Hindi fluent-speaker rubric and training-data provenance review remain. It does not solve the remaining Indian languages. |

For the nine languages still without real samples, check commercially permissible CPU models before considering a **bounded Indic Parler evaluation** after gated access, license/data review, and a verified compute/cost plan. Use the same three cases and fluent listening gate in each language. This does not authorize a GPU, cloud deployment, large weight download, or premium speech calls. Existing Edge and explicit premium options remain available in the beta where supported; Odia currently lacks an Edge voice.

## Acceptance evidence to collect

1. Review every translated script with a fluent speaker before using it to judge the model. Use the [review form](AUDIO_NATIVE_REVIEW_TEMPLATE.md) for each language, revision and three-case run.
2. Save exact model revision, license record, hardware, synthesis wall time, audio duration, cost and decodable sample for every language. Report failures rather than skipping them.
3. Expand the common corpus to longer narration, education, emotion, mixed English, and regional names. Use fluent-speaker scoring for intelligibility, pronunciation, naturalness and story fit. Define the percentage calculation before applying the 100%/90% targets.
4. Generate a complete project and download for every primary language, then every secondary language. Check narration, captions and saved asset reuse.
