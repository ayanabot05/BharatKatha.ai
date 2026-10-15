# Phase 0 deployment handoff

## Verified status (15 October 2026)

- Cloud Run service `vidbharat-image-worker` is ready in `asia-south1`.
- Its URL is `https://vidbharat-image-worker-3biemw3ouq-el.a.run.app`.
- No main API service was listed by `gcloud run services list`.
- The additive `001_phase_zero.sql` migration was applied to the configured Supabase database.
- Frontend build and responsive checks passed locally. Public deployment has not been tested.

## 1. Deploy the main backend

Use the existing Dockerfile, cloud build configuration and `compose.yaml` on one
continuously running Google Cloud VM with HTTPS. Project: `ayana-video-studio`;
region: `asia-south1`. Keep one API process because background image/render jobs
are in-process. Do not deploy this backend as a default scale-to-zero Cloud Run
service. See `README.md` in this directory for VM, IAM and storage preparation.

Build in Google Cloud, not on the laptop. Set the backend values from
`beta.env.example`: existing Supabase URL, JWT secret, admin account, managed AI
credentials/attached identity, private GCS bucket, secure cookies. Run
`python migrate.py` in the cloud environment before starting the release.

Use `BETA_REGISTRATION=false` and set `BETA_INVITE_EMAILS` to the specific friends
allowed to register. Existing accounts can still log in. Set
`PERSONALIZED_HOOKS=false`. Production write limits are 30/minute and 200/day per
signed-in user, in addition to workflow-specific quotas. Failed attempts count
as requests. Anonymous traffic is limited by the trusted connection IP.

If using the existing image-worker bridge, follow `image-worker/README.md` for
its authentication and provider variables. The worker URL is not the main API URL.

## 2. Connect Vercel

After the main API has a working HTTPS domain:

```powershell
cd frontend
node scripts/configure-vercel.cjs https://YOUR-MAIN-API-DOMAIN
```

Commit the generated `frontend/vercel.json`. In Vercel:

- Root directory: `frontend`.
- Build: `npm run build`; output: `build`.
- Set `REACT_APP_BACKEND_URL=/` (never localhost, never the image-worker URL).
- Set `GENERATE_SOURCEMAP=false`.
- Keep all database/provider secrets out of frontend variables.
- Add the exact Vercel production origin to backend `FRONTEND_URL`.
- Use `COOKIE_SECURE=true`, `COOKIE_SAMESITE=lax`; the same-origin API rewrite
  avoids reliance on cross-site browser cookies.

The checked-in config has SPA deep links and hashed-asset caching. Until the
configure command runs, there is no API proxy. Do not invite testers yet.
External API rewrites are documented by [Vercel](https://vercel.com/docs/routing/rewrites).
Long synchronous script/voice calls must be tested against Vercel proxy limits;
if they time out, use same-site app/API custom domains or move those calls to
pollable backend jobs before launching. Do not silently retry generation POSTs.

## 3. Release check

1. Open the deployed site on a phone and laptop; refresh `/dashboard` directly.
2. Register an invited tester; confirm uninvited registration is rejected.
3. Use two accounts and confirm projects/media/feedback do not cross accounts.
4. Generate a story, review content, create pictures one at a time, listen to
   voice, approve pictures, render and download. Check pauses and captions.
5. Edit a narration after pictures exist. Confirm the affected picture/audio
   require regeneration and the prior video cannot be used as current output.
6. Use Growth Coach without metrics, then with actual metrics. Missing values
   must not appear as measured zeros. Advice is a hypothesis, not a view forecast.
7. Submit feedback; verify it appears in the admin feedback inbox.
8. Test rate-limit messaging and a backend restart/interrupted-job retry.
9. Check cloud billing alerts and clean expired request-limit rows on a schedule.

## Remaining gates

The main backend, its HTTPS domain, Vercel proxy and public end-to-end test remain
unfinished. Full ten-language UI coverage and durable background jobs remain
known product limits. This release is suitable for supervised private testing
only after the deployment checks above pass; no 95% accuracy claim is made.
