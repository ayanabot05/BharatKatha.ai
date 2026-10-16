"""Dispatch durable scene generation to a Cloud Run Job using workload identity."""

import os
import re


def job_name():
    values = (os.environ.get("GOOGLE_CLOUD_PROJECT", ""),
              os.environ.get("GOOGLE_CLOUD_REGION", "asia-south1"),
              os.environ.get("CLOUD_SCENE_JOB", ""))
    if not all(re.fullmatch(r"[a-z][a-z0-9-]*", value) for value in values):
        raise RuntimeError("Cloud scene job configuration is incomplete")
    return f"projects/{values[0]}/locations/{values[1]}/jobs/{values[2]}"


def start(pid: str, uid: str, sid: str = "", token: str = "") -> str:
    import google.auth
    from google.auth.transport.requests import AuthorizedSession

    credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    session = AuthorizedSession(credentials)
    body = {"overrides": {"containerOverrides": [{"env": [
        {"name": "SCENE_PROJECT_ID", "value": pid},
        {"name": "SCENE_USER_ID", "value": uid},
        {"name": "SCENE_ID", "value": sid},
        {"name": "SCENE_LEASE_TOKEN", "value": token},
    ]}], "taskCount": 1}}
    try:
        response = session.post(f"https://run.googleapis.com/v2/{job_name()}:run", json=body, timeout=20)
        response.raise_for_status()
        operation = response.json().get("name", "")
    finally:
        session.close()
    if not operation:
        raise RuntimeError("Cloud Run did not return a scene operation")
    return operation
