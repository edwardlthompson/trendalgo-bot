"""ntfy.sh sink (NOTIF-01)."""

from __future__ import annotations

import os
import urllib.error
import urllib.request
from typing import Any


def ntfy_enabled() -> bool:
    return bool(os.environ.get("NTFY_TOPIC"))


def send_ntfy(title: str, body: str) -> dict[str, Any]:
    topic = os.environ.get("NTFY_TOPIC", "").strip()
    if not topic:
        return {"sent": False, "reason": "NTFY_TOPIC not set"}
    base = (os.environ.get("NTFY_BASE_URL") or "https://ntfy.sh").rstrip("/")
    url = f"{base}/{topic}"
    data = body.encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Title": title, "Content-Type": "text/plain; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return {"sent": True, "status": resp.status}
    except urllib.error.URLError as exc:
        return {"sent": False, "reason": str(exc)}
