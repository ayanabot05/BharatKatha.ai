# BharatKatha handover launcher - runs the studio for an in-person test on a phone/tablet.
#
# What it does:
#   1. Rebuilds the frontend with the UI in Telugu (configurable with -UiLang).
#   2. Starts the operator-hosted Piper HTTP voice service for Telugu narration.
#   3. Starts the FastAPI backend on 0.0.0.0:8001, serving the built frontend from
#      the same origin (so no CORS, proxy or cookie problems apply).
#
# The phone/tablet just opens the LAN URL printed at the end. Your computer must
# stay awake and on the same Wi-Fi as the device for the whole session.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File .\run_for_test.ps1
#   powershell -ExecutionPolicy Bypass -File .\run_for_test.ps1 -Voice edge
#
# Notes:
#   - These settings are passed as environment variables and WIN over backend\.env
#     (python-dotenv does not override existing variables), so .env is left untouched.
#   - ALLOW_PLACEHOLDER_RENDER is forced off so a fake sample image can never reach
#     a render during the test.

param(
  [ValidateSet("piper", "edge")][string]$Voice = "piper",
  [string]$UiLang = "te",
  [int]$Port = 8001,
  [int]$PiperPort = 5008
)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"
$py = Join-Path $backend "venv/Scripts/python.exe"

if (-not (Test-Path $py)) { throw "Python venv not found at $py" }

function Test-Port([int]$p) {
  try {
    $c = New-Object System.Net.Sockets.TcpClient
    $c.Connect("127.0.0.1", $p); $c.Close(); return $true
  } catch { return $false }
}

# Pick the LAN address the phone will use.
$lan = (Get-NetIPAddress -AddressFamily IPv4 |
  Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*' } |
  Select-Object -First 1).IPAddress
if (-not $lan) { throw "Could not find a LAN IPv4 address. Connect this computer to Wi-Fi first." }
$lanOrigin = "http://${lan}:${Port}"

Write-Host "==> Building frontend (UI language: $UiLang)..." -ForegroundColor Cyan
$env:REACT_APP_DEFAULT_UI_LANG = $UiLang
Push-Location $frontend
try { npm run build } finally { Pop-Location }
if (-not (Test-Path (Join-Path $frontend "build/index.html"))) { throw "Frontend build did not produce build/index.html" }

if ($Voice -eq "piper") {
  if (-not (Test-Port $PiperPort)) {
    Write-Host "==> Starting Piper Telugu voice service on port $PiperPort..." -ForegroundColor Cyan
    Start-Process -FilePath $py `
      -ArgumentList @("-m", "piper.http_server", "--host", "127.0.0.1", "--port", "$PiperPort", "-m", ".piper-models/te_IN-padmavathi-medium.onnx") `
      -WorkingDirectory $backend -WindowStyle Minimized
    for ($i = 0; $i -lt 30 -and -not (Test-Port $PiperPort); $i++) { Start-Sleep -Seconds 1 }
    if (-not (Test-Port $PiperPort)) { throw "Piper did not start on port $PiperPort within 30s" }
  } else {
    Write-Host "==> Piper already running on port $PiperPort." -ForegroundColor Cyan
  }
  $env:PIPER_VOICES_JSON = '{"te":{"url":"http://127.0.0.1:5008","model_id":"te_IN-padmavathi-medium","model_revision":"local-handover","license_url":"https://huggingface.co/rhasspy/piper-voices","license_status":"verified-commercial","hardware_requirements":"local CPU"}}'
  $env:TTS_PROVIDER = "piper"
} else {
  $env:TTS_PROVIDER = "edge"
}

# Test-safe overrides. load_dotenv() does not override these, so they win over backend\.env.
$env:APP_ENV = "development"
$env:SERVE_FRONTEND = "true"
$env:FRONTEND_URL = "http://localhost:3004,http://127.0.0.1:${Port},${lanOrigin}"
$env:COOKIE_SECURE = "false"
$env:ALLOW_PLACEHOLDER_RENDER = "false"
$env:ALLOW_IMAGE_FALLBACK = "false"
$env:PLACEHOLDER_USE_SAMPLES = "false"

# If port 8001 is already in use, fail loudly instead of quietly using stale data.
if (Test-Port $Port) { throw "Port $Port is already in use. Stop the old backend (or pass -Port 8002) and rerun." }

Write-Host ""
Write-Host "==================================================================" -ForegroundColor Green
Write-Host "  Open this on the phone/tablet while on the same Wi-Fi:" -ForegroundColor Green
Write-Host ""
Write-Host "      http://${lan}:${Port}" -ForegroundColor Yellow
Write-Host ""
Write-Host "  Voice provider: $Voice     UI language: $UiLang"
Write-Host "  Keep this window open. Press Ctrl+C here to stop the studio."
Write-Host "  (First run may show a Windows Firewall prompt - choose Allow on Private networks.)"
Write-Host "==================================================================" -ForegroundColor Green
Write-Host ""

Push-Location $backend
try { & $py -m uvicorn server:app --host 0.0.0.0 --port $Port } finally { Pop-Location }
