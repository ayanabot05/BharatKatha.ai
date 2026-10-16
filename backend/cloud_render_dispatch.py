"""Start the configured Cloud Run render job; never render in the production API."""

import os
import re


def job_name():
    project = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
    region = os.environ.get("GOOGLE_CLOUD_REGION", "asia-south1")
    job = os.environ.get("CLOUD_RENDER_JOB", "")
    if not all(re.fullmatch(r"[a-z][a-z0-9-]*", value) for value in (project, region, job)):
        raise RuntimeError("Cloud render job configuration is incomplete")
    return f"projects/{project}/locations/{region}/jobs/{job}"


def start(pid: str, uid: str, token: str = "") -> str:
    """Return the Cloud Run operation name after the execution is accepted."""
    import google.auth
    from google.auth.transport.requests import AuthorizedSession

    credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    session = AuthorizedSession(credentials)
    body = {"overrides": {"containerOverrides": [{"env": [
        {"name": "RENDER_PROJECT_ID", "value": pid},
        {"name": "RENDER_USER_ID", "value": uid},
        {"name": "RENDER_CLAIM_TOKEN", "value": token},
    ]}], "taskCount": 1}}
    try:
        response = session.post(f"https://run.googleapis.com/v2/{job_name()}:run", json=body, timeout=20)
        response.raise_for_status()
        operation = response.json().get("name", "")
    finally:
        session.close()
    if not operation:
        raise RuntimeError("Cloud Run did not return a render operation")
    return operation
