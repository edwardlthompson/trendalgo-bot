"""Container / API health probes (OPS4)."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any


def probe_url(url: str, *, timeout: float = 5.0) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            try:
                parsed = json.loads(body)
            except json.JSONDecodeError:
                parsed = {"raw": body[:200]}
            return {"ok": resp.status == 200, "status": resp.status, "body": parsed}
    except (urllib.error.URLError, TimeoutError) as exc:
        return {"ok": False, "error": str(exc)}


def composite_health(api_url: str) -> dict[str, Any]:
    api = probe_url(api_url)
    return {
        "api": api,
        "engine": {"ok": True, "name": "native"},
        "healthy": api.get("ok"),
    }
