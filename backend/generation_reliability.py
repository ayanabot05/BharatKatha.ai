"""Bounded retries and safe messages for generation dependencies."""
import asyncio
import logging

log = logging.getLogger("vidbharat")


def access_error(exc):
    text = str(exc).lower()
    return any(word in text for word in (
        "reauth", "invalid_grant", "credentials", "permission_denied", "403", "401",
    ))


def transient_error(exc):
    if access_error(exc):
        return False
    text = str(exc).lower()
    return (isinstance(exc, (TimeoutError, ConnectionError))
            or type(exc).__name__ in {"TransportError", "ConnectError", "ReadError", "ReadTimeout", "ConnectTimeout", "ConnectionError", "RemoteProtocolError"}
            or any(word in text for word in ("429", "502", "503", "504", "500 internal", "resource_exhausted", "overloaded", "deadline_exceeded")))


async def retry_transient(operation, label):
    for attempt in range(3):
        try:
            return await operation()
        except Exception as exc:
            if attempt == 2 or not transient_error(exc):
                raise
            log.warning("%s: temporary failure; retry %s/2 (%s)", label, attempt + 1, type(exc).__name__)
            await asyncio.sleep(2 * (attempt + 1))


def public_failure(exc, stage):
    if "did not match the narration closely enough" in str(exc):
        return "The recognized words did not match the approved narration closely enough for accurate subtitles. Your voice is saved. Retry caption timing or continue without captions."
    if access_error(exc):
        return f"{stage} is blocked by the provider's sign-in or permissions. The app operator must reconnect the service. Repeated regeneration will not fix this."
    if transient_error(exc):
        return f"{stage} could not reach the provider after automatic retries. Please check the connection and try again."
    return f"{stage} failed. Your saved work is safe. Please try again; the server log contains the cause."
