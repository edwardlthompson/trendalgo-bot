"""SMTP email notifier — env-gated (T27)."""

from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage
from typing import Any


def smtp_enabled() -> bool:
    return bool(os.environ.get("SMTP_HOST") and os.environ.get("SMTP_TO"))


def send_smtp_email(subject: str, body: str) -> dict[str, Any]:
    host = os.environ.get("SMTP_HOST", "")
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ.get("SMTP_USER", "")
    password = os.environ.get("SMTP_PASSWORD", "")
    to_addr = os.environ.get("SMTP_TO", "")
    from_addr = os.environ.get("SMTP_FROM", user or "trendalgo@localhost")

    if not host or not to_addr:
        return {"sent": False, "reason": "SMTP_HOST or SMTP_TO not set"}

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg.set_content(body)

    try:
        with smtplib.SMTP(host, port, timeout=15) as smtp:
            if os.environ.get("SMTP_TLS", "1") == "1":
                smtp.starttls()
            if user and password:
                smtp.login(user, password)
            smtp.send_message(msg)
        return {"sent": True}
    except OSError as exc:
        return {"sent": False, "reason": str(exc)}
