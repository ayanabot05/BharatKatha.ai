# Decisions

| Date | Decision | Reason and constraint |
| --- | --- | --- |
| 2026-10-15 | Preserve the current studio and Growth Coach while adding providers incrementally. | Existing project/edit/export gates contain valuable work and must not regress. |
| 2026-10-15 | Add Piper through a separately hosted HTTP service, with per-language endpoints. | No model weights are placed in the API process. One Telugu voice was downloaded to an ignored local evaluation directory; exact production rights and runtime remain deployment gates. |
| 2026-10-15 | Require a voice manifest with model revision and commercial license review before Piper appears in the UI. | The Hindi pratham model card lists a noncommercial dataset; a repository-level license cannot clear every voice. |
| 2026-10-15 | Never switch a failed selected TTS route to another provider automatically. | Prevent unapproved paid calls and misleading provider evidence. |
| 2026-10-15 | Require request-level selection and a typed budget for configured premium TTS. | An environment default alone must not cause a paid speech call. Operator all-in rates and a hard INR cap now gate preview and narration; current pricing and invoice reconciliation remain production tasks. |
| 2026-10-15 | Keep Edge as the legacy configured default until an open voice passes quality and latency review. | Telugu Piper generated decodable samples, but native-speaker quality has not been accepted. |
| 2026-10-15 | Do not automatically retry premium narration or cloud caption transcription. | A failed call may still be billed; a retry could exceed the creator's authorized budget. |
| 2026-10-15 | Defer image and video integration until audio feasibility results exist. | Explicit founder implementation order. |

These decisions do not authorize cloud deployment or paid inference.
