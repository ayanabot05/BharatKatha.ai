"""Fetch the pinned Telugu Piper voice from private GCS, then serve on Cloud Run."""

import hashlib
import os
from pathlib import Path
import subprocess

from google.cloud import storage

EXPECTED_SHA256 = "414aa5960d91ceb6e45bbdf8c27fdc71af09f205130d7be4e99470f3c2cfa57d"
MODEL_NAME = "te_IN-padmavathi-medium.onnx"


def prepare_model():
    bucket_name = os.environ["VOICE_MODEL_BUCKET"]
    prefix = os.environ["VOICE_MODEL_PREFIX"].strip("/")
    if not prefix:
        raise RuntimeError("VOICE_MODEL_PREFIX is required")
    bucket = storage.Client().bucket(bucket_name)
    folder = Path("/tmp/piper-model")
    folder.mkdir(exist_ok=True)
    for filename in (MODEL_NAME, MODEL_NAME + ".json"):
        path = folder / filename
        bucket.blob(f"{prefix}/{filename}").download_to_filename(str(path), timeout=180)
    digest = hashlib.sha256((folder / MODEL_NAME).read_bytes()).hexdigest()
    if digest != EXPECTED_SHA256:
        raise RuntimeError("Telugu Piper model hash does not match the reviewed version")
    return folder / MODEL_NAME


if __name__ == "__main__":
    model = prepare_model()
    subprocess.run(["python", "-m", "piper.http_server", "--host", "0.0.0.0",
                    "--port", os.environ.get("PORT", "8080"), "--model", str(model)], check=True)
