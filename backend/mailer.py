"""Outbound email with an honest fallback.

A password reset link is only useful if it actually reaches the person. This
uses the operator's own SMTP account — free with, for example, a Gmail app
password — configured through the environment:

    SMTP_HOST, SMTP_PORT (default 587), SMTP_USER, SMTP_PASSWORD,
    SMTP_FROM (defaults to SMTP_USER), SMTP_TLS (default "true"; port 465
    switches to implicit TLS automatically)

When SMTP is not configured, the message is written to the server log instead
and ``delivery_mode()`` reports ``"manual"``. The UI reads that via
``/api/meta`` so it can say "contact support" rather than promising an inbox
that will never receive anything.
"""
from __future__ import annotations

import os
import ssl
import smtplib
import asyncio
from email.message import EmailMessage

from core import log


def configured() -> bool:
    return bool(os.environ.get("SMTP_HOST") and os.environ.get("SMTP_USER")
                and os.environ.get("SMTP_PASSWORD"))


def delivery_mode() -> str:
    """'email' when mail can actually be sent, otherwise 'manual'."""
    return "email" if configured() else "manual"


def base_url() -> str:
    """Public origin used inside emailed links."""
    explicit = (os.environ.get("PUBLIC_BASE_URL") or "").strip()
    if explicit:
        return explicit.rstrip("/")
    front = (os.environ.get("FRONTEND_URL") or "").strip()
    if front:
        first = front.split(",")[0].strip()
        if first:
            return first.rstrip("/")
    return "http://localhost:3004"


def reset_link(token: str) -> str:
    return f"{base_url()}/reset-password?token={token}"


def _send_blocking(to: str, subject: str, body: str) -> bool:
    host = os.environ["SMTP_HOST"]
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ["SMTP_USER"]
    password = os.environ["SMTP_PASSWORD"]
    sender = os.environ.get("SMTP_FROM") or user

    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    context = ssl.create_default_context()
    if port == 465:
        with smtplib.SMTP_SSL(host, port, timeout=15, context=context) as smtp:
            smtp.login(user, password)
            smtp.send_message(msg)
    else:
        with smtplib.SMTP(host, port, timeout=15) as smtp:
            if os.environ.get("SMTP_TLS", "true").lower() == "true":
                smtp.starttls(context=context)
            smtp.login(user, password)
            smtp.send_message(msg)
    return True


async def send(to: str, subject: str, body: str, *, also_log: str = "") -> bool:
    """Send mail, or log it when SMTP is not configured. Never raises."""
    if not configured():
        log.warning("MAIL (SMTP not configured, operator must relay) to=%s subject=%s%s",
                    to, subject, f"\n{also_log}" if also_log else "")
        return False
    try:
        return await asyncio.to_thread(_send_blocking, to, subject, body)
    except Exception as exc:  # noqa: BLE001 - a mail failure must not 500 a request
        log.error("MAIL delivery failed to=%s (%s: %s)", to, type(exc).__name__, exc)
        if also_log:
            log.warning("MAIL fallback link: %s", also_log)
        return False
