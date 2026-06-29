"""BTC/USD spot quote for settlement amounts (user-initiated payment only)."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request


def fetch_btc_usd(*, timeout_sec: float = 10.0) -> float:
    override = os.environ.get("TRENDALGO_BTC_USD_RATE")
    if override:
        rate = float(override)
        if rate <= 0:
            raise ValueError("TRENDALGO_BTC_USD_RATE must be positive")
        return rate
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
    req = urllib.request.Request(
        url, headers={"Accept": "application/json", "User-Agent": "TrendAlgo/1.0"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            payload = json.loads(resp.read().decode())
        rate = float(payload["bitcoin"]["usd"])
    except (urllib.error.URLError, TimeoutError, KeyError, TypeError, ValueError) as exc:
        raise RuntimeError("Unable to fetch BTC/USD quote") from exc
    if rate <= 0:
        raise RuntimeError("Invalid BTC/USD quote")
    return rate
