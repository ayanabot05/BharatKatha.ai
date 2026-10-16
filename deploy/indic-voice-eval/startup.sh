#!/bin/bash
set -Eeuo pipefail
exec > >(tee -a /var/log/indic-voice-eval.log) 2>&1
trap 'shutdown -h now' EXIT

echo "Starting temporary Indic voice evaluation"
PY=/opt/conda/bin/python
if [[ ! -x "$PY" ]]; then PY=$(command -v python3); fi
echo "Python: $PY"
nvidia-smi
"$PY" -c 'import torch; print("Torch:", torch.__version__, "CUDA:", torch.cuda.is_available())'
timeout --signal=TERM 2400 "$PY" -m pip install --no-cache-dir 'google-cloud-storage>=3,<4' 'google-auth>=2,<3' 'soundfile>=0.12,<1' \
  'git+https://github.com/huggingface/parler-tts.git'
timeout --signal=TERM 300 gcloud storage cp gs://ayana-video-studio-voice-eval-20261014/indic-parler/2026-10-14/demo.py /var/tmp/indic-voice-demo.py
timeout --signal=TERM 3000 "$PY" /var/tmp/indic-voice-demo.py
