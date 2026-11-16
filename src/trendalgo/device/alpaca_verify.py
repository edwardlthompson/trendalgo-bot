"""Ping Alpaca paper account to confirm API keys."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

_PAPER_ACCOUNT = "https://paper-api.alpaca.markets/v2/account"


def verify_alpaca_keys(
    key_id: str,
    secret: str,
    *,
    opener: Any | None = None,
) -> tuple[bool, str]:
    """Return (ok, message). Uses paper trading account endpoint."""
    kid = key_id.strip()
    sec = secret.strip()
    if not kid or not sec:
        return False, "Key ID and Secret are both required."
    req = urllib.request.Request(
        _PAPER_ACCOUNT,
        headers={
            "APCA-API-KEY-ID": kid,
            "APCA-API-SECRET-KEY": sec,
            "Accept": "application/json",
        },
        method="GET",
    )
    open_fn = opener or urllib.request.urlopen
    try:
        with open_fn(req, timeout=20) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8", errors="replace")[:120]
        except OSError:
            pass
        return False, f"Alpaca refused the keys (HTTP {exc.code}). {detail}".strip()
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        return False, f"Could not reach Alpaca: {exc}"
    status = str(payload.get("status") or "").strip() if isinstance(payload, dict) else ""
    if status:
        return True, f"Connected (paper account status: {status})."
    return True, "Connected to Alpaca paper API."
