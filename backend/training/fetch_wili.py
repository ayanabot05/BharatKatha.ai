"""Fetch the original WiLI corpus with source, licence and archive verification."""
import hashlib
import json
from pathlib import Path
import zipfile
import requests

ROOT = Path(__file__).resolve().parent / "data"
RECORD = "https://zenodo.org/api/records/841984"
EXPECTED_MD5 = "3dc5bd41587811ad6b0d04ae2f235f84"


def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    response = requests.get(RECORD, timeout=45)
    response.raise_for_status()
    metadata = response.json()
    if metadata["metadata"]["license"]["id"] != "odc-odbl":
        raise RuntimeError("Dataset licence changed; inspect it before training")
    source = next(f for f in metadata["files"] if f["key"] == "wili-2018.zip")
    if source["checksum"] != "md5:" + EXPECTED_MD5:
        raise RuntimeError("Source checksum differs from the reviewed release")
    archive = ROOT / source["key"]
    if not archive.exists():
        with requests.get(source["links"]["self"], stream=True, timeout=90) as download:
            download.raise_for_status()
            with archive.open("wb") as stream:
                for chunk in download.iter_content(1024 * 1024):
                    stream.write(chunk)
    raw = archive.read_bytes()
    if hashlib.md5(raw).hexdigest() != EXPECTED_MD5:
        raise RuntimeError("Downloaded archive failed verification")
    manifest = {"source": RECORD, "doi": "10.5281/zenodo.841984", "creator": "Martin Thoma",
                "title": metadata["metadata"]["title"], "license": "ODbL-1.0",
                "license_url": "https://opendatacommons.org/licenses/odbl/1-0/",
                "attribution": "WiLI-2018, Martin Thoma (2018), Wikipedia Language Identification database, DOI 10.5281/zenodo.841984.",
                "md5": EXPECTED_MD5, "sha256": hashlib.sha256(raw).hexdigest(),
                "bytes": len(raw), "download_url": source["links"]["self"]}
    (ROOT / "source_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    with zipfile.ZipFile(archive) as bundle:
        print("Archive members:", bundle.namelist(), flush=True)
        # Read known data members in place during training; do not extract arbitrary paths.
        for name in bundle.namelist():
            if name.rsplit("/", 1)[-1].lower() in {"readme.txt", "readme.md", "license.txt", "license"}:
                (ROOT / name.rsplit("/", 1)[-1]).write_bytes(bundle.read(name))
    print("Verified public dataset", manifest["bytes"], "bytes", flush=True)


if __name__ == "__main__":
    main()
