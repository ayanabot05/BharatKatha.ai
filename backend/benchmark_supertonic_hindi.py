"""Run the three real Hindi corpus probes with the pinned local Supertonic 3 model.

Evaluation only: this script does not alter the application's provider routing.
Install the isolated dependencies under .hindi-eval-packages and download the
model into .hindi-eval-model before running it.
"""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / ".hindi-eval-packages"))

import imageio_ffmpeg
import numpy as np
import psutil
import soundfile as sf
from supertonic import TTS

from audio_eval_corpus import SCRIPTS

MODEL_REVISION = "aafc6e32416a594460b32413efc49d7fe4ce6d46"
OUT = ROOT.parent / "test_reports" / "supertonic-hindi-2026-10-16"
OUT.mkdir(parents=True, exist_ok=True)
PROCESS = psutil.Process()


def profile(call):
    stop = threading.Event()
    rss_samples = []

    def sample():
        while not stop.wait(0.02):
            rss_samples.append(PROCESS.memory_info().rss)

    sampler = threading.Thread(target=sample, daemon=True)
    sampler.start()
    cpu_start = PROCESS.cpu_times()
    wall_start = time.perf_counter()
    try:
        value = call()
    finally:
        elapsed = time.perf_counter() - wall_start
        cpu_end = PROCESS.cpu_times()
        stop.set()
        sampler.join()
    cpu_seconds = (cpu_end.user + cpu_end.system) - (cpu_start.user + cpu_start.system)
    return value, {
        "wall_seconds": round(elapsed, 3),
        "process_cpu_seconds": round(cpu_seconds, 3),
        "cpu_percent_one_core_equivalent": round(100 * cpu_seconds / elapsed, 1),
        "peak_process_rss_mib": round(max(rss_samples or [PROCESS.memory_info().rss]) / 1048576, 1),
    }


def encode_mp3(wav, sample_rate, destination):
    pcm = np.asarray(wav, dtype=np.float32).reshape(-1)
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    command = [ffmpeg, "-hide_banner", "-loglevel", "error", "-f", "f32le",
               "-ar", str(sample_rate), "-ac", "1", "-i", "pipe:0", "-c:a",
               "libmp3lame", "-q:a", "2", "-y", str(destination)]
    subprocess.run(command, input=pcm.tobytes(), check=True, capture_output=True)
    probe = subprocess.run([ffmpeg, "-hide_banner", "-i", str(destination), "-f", "null", "-"],
                           capture_output=True, text=True)
    if probe.returncode:
        raise RuntimeError(f"MP3 decode failed: {probe.stderr[-500:]}")
    with sf.SoundFile(destination) as decoded:
        duration = len(decoded) / decoded.samplerate
        decoded_samples = decoded.read(dtype="float32")
        if not np.isfinite(decoded_samples).all() or np.max(np.abs(decoded_samples)) < 0.005:
            raise RuntimeError("MP3 is silent or contains invalid samples")
    return duration


def main():
    model_dir = ROOT / ".hindi-eval-model"
    if not model_dir.joinpath("LICENSE").exists():
        raise RuntimeError("Pinned model and license must exist locally")
    tts, load = profile(lambda: TTS(model="supertonic-3", model_dir=model_dir,
                                    auto_download=False, intra_op_num_threads=4))
    voice = tts.get_voice_style("M1")
    cases = {}
    for name, script in SCRIPTS["hi"].items():
        (wav, model_duration), inference = profile(
            lambda: tts.synthesize(script, voice_style=voice, lang="hi", total_steps=8)
        )
        path = OUT / f"hi_{name}_supertonic3_M1.mp3"
        duration, encoding = profile(lambda: encode_mp3(wav, tts.sample_rate, path))
        cases[name] = {
            "text": script,
            "mp3_path": str(path.resolve()),
            "mp3_bytes": path.stat().st_size,
            "mp3_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "audio_duration_seconds": round(duration, 3),
            "model_duration_seconds": round(float(np.asarray(model_duration).reshape(-1)[0]), 3),
            "inference": inference,
            "mp3_encode_and_verify": encoding,
            "signal_peak": round(float(np.max(np.abs(wav))), 4),
        }
        print(f"{name}: {inference['wall_seconds']}s inference, {duration:.2f}s MP3, "
              f"{path.stat().st_size} bytes, peak RSS {inference['peak_process_rss_mib']} MiB", flush=True)
    report = {
        "provider": "supertonic-3-local-cpu", "voice": "M1", "language": "hi",
        "model_repo": "supertone-oss-archive/supertonic-3",
        "model_revision": MODEL_REVISION,
        "license": "OpenRAIL-M; commercial use subject to use restrictions and disclosure",
        "sample_rate_hz": tts.sample_rate, "model_load": load,
        "machine_cpu_count": os.cpu_count(), "cases": cases,
        "native_speaker_review": "NOT TESTED", "studio_flow": "NOT TESTED",
    }
    (OUT / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Report: {OUT / 'report.json'}")


if __name__ == "__main__":
    main()
