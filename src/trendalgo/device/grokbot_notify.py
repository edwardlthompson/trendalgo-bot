"""Device-side Grok Bot test: local env first, then signed host API."""

from __future__ import annotations

from pathlib import Path

from trendalgo.device.host_session import try_open_host_client
from trendalgo.notifications.grokbot import grokbot_enabled, public_status, send_test


def grokbot_status_line() -> str:
    status = public_status()
    if status["enabled"]:
        return "on"
    return "off"


def send_device_test(settings_path: Path | None = None) -> tuple[bool, str]:
    """Return (ok, detail). Never raises."""
    if grokbot_enabled():
        result = send_test(wait=True)
        if result.get("sent"):
            return True, "sent"
        return False, str(result.get("reason") or "failed")
    if settings_path is None:
        return False, "not_configured"
    client = try_open_host_client(settings_path)
    if client is None:
        return False, "not_configured"
    try:
        response = client.post_grokbot_test()
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)
    if response.ok and isinstance(response.data, dict) and response.data.get("sent"):
        return True, "sent"
    detail = ""
    if isinstance(response.data, dict):
        detail = str(response.data.get("reason") or response.data.get("detail") or "")
    return False, detail or "host_failed"
