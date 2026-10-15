"""Small-beta admission controls. PostgreSQL counters are atomic across requests.

Generation workers still require one API process; these counters do not make jobs durable.
"""
import hashlib
import os
import time
from fastapi import HTTPException
from core import db, decode

_local = {}


async def consume(key, limit, seconds):
    now = int(time.time())
    window = now // seconds
    bucket = hashlib.sha256(f"{key}:{seconds}:{window}".encode()).hexdigest()
    if hasattr(type(db), "execute"):
        row = await db.execute("""INSERT INTO request_limits(bucket, count, expires_at)
            VALUES (%s, 1, to_timestamp(%s)) ON CONFLICT(bucket)
            DO UPDATE SET count=request_limits.count + 1 RETURNING count""",
            (bucket, (window + 2) * seconds), fetchone=True)
        count = row["count"]
    elif os.environ.get("APP_ENV") == "production":
        raise RuntimeError("Phase 0 production rate limits require Supabase")
    else:
        # Development only; bounded memory, no external service needed.
        for old in [k for k, (_, expiry) in _local.items() if expiry <= now]:
            _local.pop(old, None)
        count = _local.get(bucket, (0, 0))[0] + 1
        _local[bucket] = (count, (window + 1) * seconds)
    return count <= limit, seconds - now % seconds


def identity(request):
    token = request.cookies.get("access_token")
    if not token and request.headers.get("authorization", "").startswith("Bearer "):
        token = request.headers["authorization"][7:]
    if token:
        try:
            return "user:" + decode(token)
        except HTTPException:
            pass
    # Do not trust an arbitrary X-Forwarded-For header from the public internet.
    return "ip:" + (request.client.host if request.client else "unknown")
