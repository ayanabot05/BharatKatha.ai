# Phase 0 changes and verification — 15 October 2026

## Implemented

- Compact cream/sage/rose landing with one retained phone demonstration and six moving style cards.
- Responsive dashboard with 12 stories per page and small single-image previews.
- Lazy route loading: initial JavaScript measured at about 121 KB gzip (previous build about 278 KB).
- Missing Growth Coach metrics remain unknown; beginner planning works from a topic and goal.
- Settings uses the signed-in account and removes inaccurate provider/subscription information.
- Feedback form in settings/export; persisted, unreviewed, optional training consent off by default.
- Creator category/audience/platform are passed into generation and review and stored in Supabase.
- Narration changes invalidate stale pictures, audio, approval and final render.
- Stable prompt configuration; automatic personalization disabled by default; no automatic training.
- Supabase indexes, brief/contract persistence, atomic production request counters, invited registration.
- Vercel SPA/cache/proxy configuration helper, deployment handoff, revised code-map README.
- Removed two unused legacy landing stylesheets after confirming no imports remained.

## Evidence

- Backend suite: 197 tests passed, plus 6 unittest subtests, before the final no-metrics guard test.
- Final targeted backend checks (including the new no-metrics guard and startup): 28 passed.
- Frontend existing workflow suite: 6 tests passed.
- Production frontend build passed.
- Headless Edge layout checks: landing/dashboard/coach/settings at 320, 390, 768, 1440 pixels, no horizontal overflow or page exceptions. API responses were fixtures; this is layout verification, not live end-to-end generation.
- Screenshots saved beside this report; mobile landing and desktop dashboard inspected visually.
- Real Supabase pagination query executed successfully. Migration 001 applied.
- A faulty early mock wrote one synthetic feedback row; the mock was fixed and the exact verified test row removed. User feedback was not removed.
- Cloud Run service list confirmed only the image worker, not the main application backend.

## Open release gates

Main backend deployment, HTTPS origin, Vercel API proxy setup and public end-to-end generation test remain pending. Full UI translation is incomplete. Existing background jobs require one always-running backend and are not a durable queue. Redis was not added: current small-beta counters use Supabase instead. No fresh content-accuracy percentage or live full-video score is claimed by these engineering checks.
