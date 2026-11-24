"""Ping Alpaca paper account to confirm API keys."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

_PAPER_ACCOUNT = "https://paper-api.alpaca.markets/v2/account"
_LIVE_ACCOUNT = "https://api.alpaca.markets/v2/account"


def _probe_alpaca(
    url: str, kid: str, sec: str, open_fn: Any
) -> tuple[bool, int | None, dict[str, Any] | None, str]:
    req = urllib.request.Request(
        url,
        headers={
            "APCA-API-KEY-ID": kid,
            "APCA-API-SECRET-KEY": sec,
            "Accept": "application/json",
        },
        method="GET",
    )
    try:
        with open_fn(req, timeout=20) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
            return True, 200, payload if isinstance(payload, dict) else {}, ""
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8", errors="replace")[:120]
        except OSError:
            pass
        return (
            False,
            int(exc.code),
            None,
            f"Alpaca refused the keys (HTTP {exc.code}). {detail}".strip(),
        )
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        return False, None, None, f"Could not reach Alpaca: {exc}"


def verify_alpaca_keys(
    key_id: str,
    secret: str,
    *,
    opener: Any | None = None,
) -> tuple[bool, str]:
    """Return (ok, message). Auto-detects paper (PK*) vs live (AK*) Alpaca endpoint."""
    kid = key_id.strip()
    sec = secret.strip()
    if not kid or not sec:
        return False, "Key ID and Secret are both required."
    open_fn = opener or urllib.request.urlopen
    endpoints = (
        [("live", _LIVE_ACCOUNT), ("paper", _PAPER_ACCOUNT)]
        if kid.upper().startswith("AK")
        else [("paper", _PAPER_ACCOUNT), ("live", _LIVE_ACCOUNT)]
    )
    last_err = ""
    for mode, url in endpoints:
        ok, code, payload, err = _probe_alpaca(url, kid, sec, open_fn)
        if ok and payload is not None:
            status = str(payload.get("status") or "").strip()
            equity_raw = payload.get("equity")
            equity_s = ""
            if equity_raw is not None:
                try:
                    equity_s = f" · equity: ${float(equity_raw):,.2f}"
                except (TypeError, ValueError):
                    pass
            if status:
                return True, f"Connected to Alpaca ({mode} · status: {status}{equity_s})."
            return True, f"Connected to Alpaca ({mode} API{equity_s})."
        last_err = err
        if code not in (401, 403):
            break
    return False, last_err or "Could not verify Alpaca keys."
