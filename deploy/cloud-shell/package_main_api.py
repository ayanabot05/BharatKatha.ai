"""Create a small, allowlisted source archive for the approved API build."""
import hashlib
import argparse
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[2]
PREFIX = "bharatkatha-main-api-build-20261016"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', choices=('main-api', 'telugu-workers'), default='main-api')
    target = parser.parse_args().target
    prefix = PREFIX if target == 'main-api' else 'bharatkatha-telugu-workers-build-20261016'
    files = list((ROOT / "backend").glob("*.py"))
    files += [ROOT / "backend/requirements-cloud.txt"]
    files += list((ROOT / "backend/fonts").glob("*.ttf"))
    files += list((ROOT / "backend/fonts").glob("*.txt"))
    files += list((ROOT / "backend/fonts").glob("*.md"))
    files += list((ROOT / "backend/migrations").glob("*.sql"))
    if target == 'main-api':
        files += [ROOT / "deploy/main-api/Dockerfile", ROOT / "deploy/main-api/cloudbuild.yaml"]
    else:
        files += [ROOT / 'deploy/voice-piper/Dockerfile', ROOT / 'deploy/voice-piper/cloudbuild.yaml',
                  ROOT / 'deploy/voice-piper/entrypoint.py', ROOT / 'deploy/render-worker/Dockerfile',
                  ROOT / 'deploy/render-worker/cloudbuild.yaml']
    entries = {p.relative_to(ROOT).as_posix(): p.read_bytes() for p in sorted(files)}
    entries[".gcloudignore"] = b".git\n*.zip\n*.log\n**/.env\n**/env.txt\n**/__pycache__\n"
    entries[".dockerignore"] = b".git\n*.zip\n*.log\n**/.env\n**/env.txt\n**/__pycache__\n"
    manifest = "".join(f"{hashlib.sha256(data).hexdigest()}  {name}\n" for name, data in sorted(entries.items()))
    entries["SOURCE_SHA256SUMS"] = manifest.encode()
    out = ROOT / "deliverables" / f"{prefix}.zip"
    out.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(entries.items()):
            archive.writestr(f"{prefix}/{name}", data)
    with zipfile.ZipFile(out) as archive:
        assert archive.testzip() is None
        for name, data in entries.items():
            assert archive.read(f"{prefix}/{name}") == data
    print(f"Archive: {out}")
    print(f"Files: {len(entries)}; bytes: {out.stat().st_size}")
    print(f"SHA256: {hashlib.sha256(out.read_bytes()).hexdigest()}")


if __name__ == "__main__":
    main()
