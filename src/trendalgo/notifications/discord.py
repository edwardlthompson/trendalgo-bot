"""Discord webhook notifier — env-gated (T27)."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


def discord_enabled() -> bool:
    return bool(os.environ.get("DISCORD_WEBHOOK_URL"))


def send_discord_message(content: str, *, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    url = os.environ.get("DISCORD_WEBHOOK_URL", "")
    if not url:
        return {"sent": False, "reason": "DISCORD_WEBHOOK_URL not set"}
    payload: dict[str, Any] = {"content": content}
    if extra:
        payload.update(extra)
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return {"sent": True, "status": resp.status}
    except urllib.error.URLError as exc:
        return {"sent": False, "reason": str(exc)}
