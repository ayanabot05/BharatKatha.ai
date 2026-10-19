"""Private Cloudflare R2 storage (S3-compatible, zero egress fee).

R2 is the durable home for media only: rendered MP4s, scene images and
narration audio. Text data (users, projects, scripts, billing, growth) stays in
Postgres - R2 is object storage, not a database.

Why R2 in front of Supabase Storage or GCS: object egress is billed by the
gigabyte and video playback is almost all egress. R2 charges nothing for it.

Nothing is committed. Configuration comes from the environment:

    R2_BUCKET               bucket name. Setting this is what enables R2.
    R2_ACCOUNT_ID           Cloudflare account id; used to derive the endpoint
    R2_ENDPOINT             full S3 endpoint, overrides R2_ACCOUNT_ID
    R2_ACCESS_KEY_ID        R2 API token access key id
    R2_SECRET_ACCESS_KEY    R2 API token secret
    R2_PREFIX               optional key prefix, default "media"

The module never raises on import, so the app still boots when R2 is absent.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import PurePosixPath

# Endpoint for the R2 S3 API. Derived from the account id unless set directly.
ENDPOINT_TEMPLATE = "https://{account}.r2.cloudflarestorage.com"

# R2 speaks S3 signature v4 only. "auto" is the region R2 expects.
REGION = "auto"


def validate_object_name(name: str) -> str:
    """Reject traversal and empty segments before anything reaches R2."""
    parts = name.split("/")
    if (not name or "\\" in name or PurePosixPath(name).is_absolute()
            or any(part in ("", ".", "..") for part in parts)):
        raise ValueError("Invalid cloud object name")
    return name


def bucket() -> str:
    return os.environ.get("R2_BUCKET", "").strip()


def endpoint() -> str:
    explicit = os.environ.get("R2_ENDPOINT", "").strip()
    if explicit:
        return explicit.rstrip("/")
    account = os.environ.get("R2_ACCOUNT_ID", "").strip()
    return ENDPOINT_TEMPLATE.format(account=account) if account else ""


def prefix() -> str:
    return os.environ.get("R2_PREFIX", "media").strip().strip("/")


def configured() -> bool:
    """True only when a bucket, an endpoint and usable credentials all exist."""
    return bool(
        bucket()
        and endpoint()
        and os.environ.get("R2_ACCESS_KEY_ID", "").strip()
        and os.environ.get("R2_SECRET_ACCESS_KEY", "").strip()
    )


def key_for(name: str) -> str:
    """Map an app storage path to an R2 object key."""
    name = validate_object_name(name)
    prefix_value = prefix()
    return f"{prefix_value}/{name}" if prefix_value else name


@lru_cache(maxsize=1)
def client():
    import boto3
    from botocore.config import Config

    return boto3.client(
        "s3",
        endpoint_url=endpoint(),
        aws_access_key_id=os.environ.get("R2_ACCESS_KEY_ID", "").strip(),
        aws_secret_access_key=os.environ.get("R2_SECRET_ACCESS_KEY", "").strip(),
        region_name=REGION,
        config=Config(signature_version="s3v4", retries={"max_attempts": 3, "mode": "standard"}),
    )


def upload(name: str, data: bytes, content_type: str):
    """Store one object. Returns {"path": name} to match the GCS contract."""
    key = key_for(name)
    body = {"Bucket": bucket(), "Key": key, "Body": data,
            "ContentType": content_type or "application/octet-stream"}
    try:
        # Object names carry a fresh id, so a collision means a bug, not a retry.
        # IfNoneMatch refuses to silently overwrite. Older botocore lacks the arg.
        client().put_object(**body, IfNoneMatch="*")
    except TypeError:
        client().put_object(**body)
    return {"path": name}


def download(name: str):
    key = key_for(name)
    try:
        obj = client().get_object(Bucket=bucket(), Key=key)
    except Exception as exc:  # noqa: BLE001 - normalise to the GCS contract
        if type(exc).__name__ in ("NoSuchKey", "404", "ClientError"):
            raise FileNotFoundError("Media object not found") from exc
        raise
    return obj["Body"].read(), obj.get("ContentType") or "application/octet-stream"


def delete(name: str) -> None:
    """Remove one object. Deleting media you no longer serve stops the meter."""
    client().delete_object(Bucket=bucket(), Key=key_for(name))


def exists(name: str) -> bool:
    """True when the object is already in R2. Used to make migrations idempotent."""
    from botocore.exceptions import ClientError
    try:
        client().head_object(Bucket=bucket(), Key=key_for(name))
        return True
    except ClientError as exc:
        code = str(exc.response.get("Error", {}).get("Code", ""))
        if code in ("404", "NoSuchKey", "NotFound"):
            return False
        raise


def presigned_url(name: str, expires_in: int = 3600, filename: str = "",
                  content_type: str = "") -> str:
    """Short-lived direct URL so the browser reads from R2, not through the API.

    Presigning is free and the download itself costs no egress, so playback
    stops consuming backend bandwidth. Returns "" when R2 is not configured.
    """
    if not configured():
        return ""
    params = {"Bucket": bucket(), "Key": key_for(name)}
    if content_type:
        params["ResponseContentType"] = content_type
    if filename:
        safe = filename.replace('"', "")
        params["ResponseContentDisposition"] = f'attachment; filename="{safe}"'
    return client().generate_presigned_url(
        "get_object", Params=params, ExpiresIn=max(60, int(expires_in)))
