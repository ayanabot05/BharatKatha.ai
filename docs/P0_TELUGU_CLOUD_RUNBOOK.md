# P0 controlled verification — Telugu audio and cloud access

Updated: 15 October 2026. These commands are for the founder's Windows PowerShell, outside the restricted Codex sandbox. Run them only against a disposable Telugu project with an approved current script and real, approved scene images. The app's render route rejects placeholder or unapproved images. Keep the existing backend `.env`; do not paste credentials into chat. Do not run image, script, or premium voice generation as part of this check.

## Telugu Piper journey

Open three PowerShell windows. In window 1, run the already installed Piper runtime and model:

```powershell
Set-Location 'C:\Users\gunak\Downloads\BharatKatha.ai\backend'
$model = '.\.piper-models\te_IN-padmavathi-medium.onnx'
if (-not (Test-Path '.\.piper-eval\Scripts\python.exe') -or -not (Test-Path $model)) { throw 'Existing Piper runtime or Telugu model is missing' }
if ((Get-FileHash $model -Algorithm SHA256).Hash -ne '414AA5960D91CEB6E45BBDF8C27FDC71AF09F205130D7BE4E99470F3C2CFA57D') { throw 'Unexpected Telugu model hash' }
.\.piper-eval\Scripts\python.exe -m piper.http_server --host 127.0.0.1 --port 5008 --model $model
```

The hash check stops the run if the installed model differs from the evaluated one. In window 2, set the explicit local voice and start the existing backend. The `.env` database and storage connection must already work locally.

```powershell
Set-Location 'C:\Users\gunak\Downloads\BharatKatha.ai\backend'
$voice = @{ te = @{ url = 'http://127.0.0.1:5008'; model_id = 'te_IN-padmavathi-medium'; model_revision = 'sha256:414aa5960d91ceb6e45bbdf8c27fdc71af09f205130d7be4e99470f3c2cfa57d'; license_url = 'https://huggingface.co/rhasspy/piper-voices/commit/ff43c1e79f98a765202dcfb03710851f9ec4ff2e'; license_status = 'verified-commercial'; hardware_requirements = 'Windows x64 CPU' } }
$env:PIPER_VOICES_JSON = ConvertTo-Json $voice -Compress -Depth 4
$env:TTS_PROVIDER = 'piper'
$env:TTS_PREMIUM_RATES_JSON = '{}'
python -c "import uvicorn, fastapi, PIL, imageio_ffmpeg; print('Backend Python dependencies: PASS')"
python -m uvicorn server:app --host 127.0.0.1 --port 8000
```

The `verified-commercial` value reflects the preliminary Piper model and training-data terms check; a final attribution and distribution review is still required before production. In window 3:

```powershell
Set-Location 'C:\Users\gunak\Downloads\BharatKatha.ai\frontend'
npm start
```

Open `http://localhost:3003` and sign in locally. Open the disposable Telugu project. Confirm its approved script and each scene's real approved picture. In Audio Studio choose **Piper**, play the configured voice preview, then select **Generate narration for all scenes** once. Listen to the saved audio player and confirm the estimated-caption warning appears. Continue to Render with burn-in captions on; select **Render my video** once. Wait for `done`, play the video, inspect subtitle synchronization, download MP4 and SRT. In browser DevTools Network, record the duration, status code and response size for `/api/voice/preview`, `/api/projects/<id>/audio/ai`, `/api/projects/<id>/render`, and `/api/media/<video-path>`. Do not record cookies or authorization headers. Save screenshots of preview playback, saved audio/warning, render completion and MP4 playback in the ignored `test_reports/p0-telugu-local/` directory.

Validate the downloaded video in PowerShell (replace only the local file path):

```powershell
$mp4 = Join-Path $HOME 'Downloads\<downloaded-video>.mp4'
if (-not (Test-Path $mp4)) { throw 'Downloaded MP4 missing' }
Set-Location 'C:\Users\gunak\Downloads\BharatKatha.ai\backend'
python -c "import render, subprocess, sys; p=sys.argv[1]; info=subprocess.run([render.FF,'-hide_banner','-i',p],capture_output=True,text=True).stderr; assert 'Video:' in info and 'Audio:' in info, 'Missing video or audio stream'; assert render.duration(p)>0, 'Invalid duration'; render.run(['-i',p,'-f','null','NUL']); print('MP4 video/audio streams and full decode: PASS; duration:',render.duration(p))" $mp4
Get-FileHash $mp4 -Algorithm SHA256
```

The current backend `.venv` lacks Pillow; the system `python` passed the listed dependency imports on 15 October. This verification uses the application's bundled FFmpeg through `render.FF`; `ffprobe` is not installed on the checked host. If the backend starts with a different Python environment, run the dependency preflight there first.

Record each stage as PASS, FAIL or BLOCKED in `docs/TEST_RESULTS.md` with actual timing and file evidence. A decodable MP4 does not by itself prove Telugu pronunciation or subtitle synchronization; those need listening and playback review. Stop the three foreground processes with Ctrl+C after collecting evidence. Do not repeat the earlier stalled in-sandbox preview attempt.

## Google Cloud authentication and read-only inventory

The founder restored CLI authentication. The live inventory is complete in the [read-only cloud audit](CLOUD_READ_ONLY_AUDIT_2026-10-15.md). These commands remain available to reproduce its core checks; no second login is needed while the session works:

```powershell
gcloud config get-value project
gcloud projects describe ayana-video-studio --format='json(projectId,lifecycleState)'
gcloud billing projects describe ayana-video-studio --format='json(billingEnabled,billingAccountName)'
gcloud billing accounts list --format='table(name,displayName,open)'
gcloud run services list --project=ayana-video-studio --format='table(name,region,status.url)'
gcloud run jobs list --project=ayana-video-studio --format='table(name,region)'
gcloud compute regions list --project=ayana-video-studio --format='table(name,quotas.metric,quotas.limit,quotas.usage)'
gcloud compute accelerator-types list --project=ayana-video-studio --filter='name~nvidia-l4' --format='table(name,zone)'
```

The accelerator type list shows catalog availability, not capacity or an allocated GPU quota. Compute quotas and Cloud Run GPU quotas are distinct; the audit measured both through read-only APIs. Free-trial status, remaining credit and expiry still require the founder's own **Billing → Overview/Credits** view; `billingEnabled` alone does not establish trial eligibility. Do not enter a password into chat or this in-app browser. No GPU deployment is authorized.

## Indic Parler access gate

[The publisher's model card](https://huggingface.co/ai4bharat/indic-parler-tts) lists Apache-2.0 weights, 0.9B F32 parameters, a contact-sharing access gate and supported languages that include all 11 app languages. The training-data table includes a `CC V1` entry whose commercial terms need clarification before production. The model card does not establish a minimum host RAM or VRAM requirement. A controlled evaluation requires accepted gated terms on the founder's Hugging Face account, authenticated download access, enough disk/RAM or an explicitly approved GPU budget, and native-speaker review. [Cloud Run's L4 configuration](https://cloud.google.com/run/docs/configuring/services/gpu) offers 24 GiB VRAM with at least 4 CPU and 16 GiB system RAM; those are platform requirements, not a measured Indic Parler requirement or proof of project quota. Do not treat a public ONNX conversion as resolving gating, data rights or hardware feasibility.
