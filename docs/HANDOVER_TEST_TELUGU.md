# Handover test — Telugu, in person, on a phone/tablet

Goal: watch your father create one Telugu video end-to-end on his own, and find
out where he gets stuck. This is a **usability test**, not a launch — the app is
still a supervised private beta.

## Before you start

- Your computer must stay awake and on the **same Wi-Fi** as the phone/tablet.
- The first solo video takes a while (script + review + 5 images + voice + render).
  Budget 10–20 minutes and keep the phone awake.
- Everything runs on your computer; nothing is published publicly.

## Start the studio

Open PowerShell in the project folder and run:

```powershell
powershell -ExecutionPolicy Bypass -File .\run_for_test.ps1
```

Wait for the green box, then open the printed address on the phone/tablet:

```
http://192.168.1.6:8001
```

If Windows Firewall asks, choose **Allow** on **Private networks**. If the phone
cannot load it, confirm the computer's IP with `ipconfig` and that both devices
are on the same Wi-Fi.

`-Voice edge` switches to the built-in Edge voices if Piper has trouble.
`-UiLang en` builds an English UI if you want to isolate UI language from the flow.

## Set him up (do this once, then hand over the phone)

The sign-in screen is still in English, so create and sign him in yourself:

1. Create an account (any name/email/password; it is invite-free locally).
2. Sign in and land on the dashboard.
3. Confirm the interface is in **Telugu**. If not, pick తెలుగు in the language box.
4. Hand the phone over and say only: **"ఒక టెలుగు వీడియో తయారు చేయండి"**
   (make one Telugu video). Do not guide step by step.

## What to watch (say nothing, just note)

- Does he understand each step without you explaining?
- Where does he pause, scroll back, or tap the wrong thing?
- Does he notice the language/region/category/length/tone choices?
- After the story is written, does he find **review → approve**?
- Does he understand why pictures must be approved before the video?
- Does the voice preview and narration make sense to him?
- Can he find and download the final video?

## Supporting the flow (only if he is truly stuck)

The flow is: **Idea → Script (review + approve) → Style → Scenes (approve each
picture) → Voice (Piper) → Render → Download.** The app blocks progress until the
script is reviewed/approved and every picture is approved — that is intentional,
so expect those gates.

## Capture his feedback

- In the app, the feedback form records entries as `beta_feedback`.
- As the admin, read the newest entries at `GET /api/feedback` (or the admin UI).
- Also note, in your own words: the exact moment he got stuck, and what he said.

## Known limits to set expectations

- Video is animated still pictures with camera motion — no moving scenes or lip sync.
- Telugu captions are timed from the script estimate (not word-level), so they are
  approximate.
- Only Telugu, Hindi and English are enabled; other languages show "Coming Soon".
- Growth Coach still takes manually entered statistics.

## Stop

Press **Ctrl+C** in the PowerShell window to stop the backend. Close the minimised
Piper window to stop the voice service.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| Phone can't open the page | Same Wi-Fi? Allow the firewall prompt on Private networks. Recheck the IP with `ipconfig`. |
| "Port 8001 already in use" | Close the old backend window, or run `.\run_for_test.ps1 -Port 8002`. |
| Narration fails | Rerun with `-Voice edge`. |
| Pictures fail | Check the image worker is reachable, or the Vertex/provider quota. |
| Pictures fail with "sign-in or permissions" | Image review follows `TEXT_PROVIDER` in `backend/.env`. With `developer,vertex` it reviews using `GEMINI_API_KEY`, avoiding the gcloud ADC login (which expires). If it still fails, check the image worker and the Gemini key. |
| UI is English | Set the language box to తెలుగు, or rebuild with `-UiLang te`. |
