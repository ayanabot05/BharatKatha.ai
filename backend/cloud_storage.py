"""Private GCS storage. Credentials come from the worker's service account."""
from functools import lru_cache
from pathlib import PurePosixPath


def validate_object_name(name):
    parts = name.split("/")
    if (not name or "\\" in name or PurePosixPath(name).is_absolute()
            or any(part in ("", ".", "..") for part in parts)):
        raise ValueError("Invalid cloud object name")
    return name


@lru_cache(maxsize=1)
def client():
    from google.cloud import storage
    return storage.Client()


def upload(bucket, name, data, content_type):
    blob = client().bucket(bucket).blob(validate_object_name(name))
    blob.upload_from_string(data, content_type=content_type, if_generation_match=0, timeout=120)
    return {"path": name}


def download(bucket, name):
    from google.api_core.exceptions import NotFound
    blob = client().bucket(bucket).blob(validate_object_name(name))
    try:
        data = blob.download_as_bytes(timeout=120)
    except NotFound as exc:
        raise FileNotFoundError("Media object not found") from exc
    return data, blob.content_type or "application/octet-stream"
