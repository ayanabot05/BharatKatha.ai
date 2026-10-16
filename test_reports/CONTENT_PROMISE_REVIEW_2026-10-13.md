# Content promise review — 13 October 2026

## Goal

When a creator selects or enters an idea, the script must deliver its stated people, actions, order, hook, and payoff. Content takes priority over a fixed word count or scene count.

## Changes

- Suggested ideas now include a concrete payoff. Selecting one passes its title, story promise, hook, and required payoff to script generation.
- Script generation extracts a server-owned content checklist from the selected idea, writes against it, and audits the draft before returning it. One revision is attempted if a promised beat is missing. A draft that still fails is withheld.
- Script review audits the same saved checklist after creator edits. Missing content blocks approval and appears in the Script Studio. The checklist is visible alongside the draft.
- Hook length, narration length, and scene count are advisory. They do not outweigh the creator's requested content.

## Content-only evidence

| Case | Original failure or promise | Result |
|---|---|---|
| Telugu pipe repair | The earlier five-scene script brought a clamp and jumped to tightening it without fitting it; the old concept review marked it complete. | The revised gate rejected that omission. A new script explicitly discovers the leak, inspects without tools, fits the four-bolt clamp, tightens it, and ends with the same dry joint. See `content_promise_retest_2026-10-13.json` and `content_generation_2026-10-13.json`. |
| Hindi selected envelope story | Hook asks why Mira returned the envelope; payoff requires the classmate's scholarship, thanks, and Mira declining a reward. | A four-scene draft delivered each of these facts and passed the content gate. See `content_generation_wallet_2026-10-13.json`. |

These are script checks only. No native-speaker review was completed for the phrasing, and two examples do not establish accuracy across all 11 creation languages. The semantic audit uses a text model and can still make mistakes; the creator's final read remains valuable.

## Verification

- Focused backend content, language, and API regressions: 137 passed.
- Frontend regression tests: 5 passed; production build passed.
- Full backend suite: 152 passed and one localhost request timed out. The timed-out test passed when rerun alone.
- `git diff --check` passed.
