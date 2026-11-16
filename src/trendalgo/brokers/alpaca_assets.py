"""Alpaca Assets API — tradable US equity universe for TradFi max scan."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

_PAPER_ASSETS = "https://paper-api.alpaca.markets/v2/assets"
_HTTP_TIMEOUT_S = 45


def fetch_tradable_us_equity_symbols(
    *,
    credentials: tuple[str, str] | None = None,
    opener: Any | None = None,
) -> list[str]:
    """GET /v2/assets?status=active&asset_class=us_equity → cleaned tradable tickers."""
    if credentials is None:
        from trendalgo.device.alpaca_vault import resolve_alpaca_credentials

        credentials = resolve_alpaca_credentials()
    if credentials is None:
        raise RuntimeError("Alpaca credentials missing")
    key, secret = credentials
    query = urllib.parse.urlencode({"status": "active", "asset_class": "us_equity"})
    url = f"{_PAPER_ASSETS}?{query}"
    req = urllib.request.Request(
        url,
        headers={
            "APCA-API-KEY-ID": key,
            "APCA-API-SECRET-KEY": secret,
            "Accept": "application/json",
        },
        method="GET",
    )
    open_fn = opener or urllib.request.urlopen
    with open_fn(req, timeout=_HTTP_TIMEOUT_S) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    if not isinstance(payload, list):
        return []
    return parse_tradable_equity_assets(payload)


def parse_tradable_equity_assets(assets: list[Any]) -> list[str]:
    """Filter Alpaca asset rows to tradable scan tickers (drop warrants/units/rights)."""
    out: list[str] = []
    seen: set[str] = set()
    for row in assets:
        if not isinstance(row, dict):
            continue
        if not bool(row.get("tradable")):
            continue
        status = str(row.get("status") or "").strip().lower()
        if status and status != "active":
            continue
        sym = str(row.get("symbol") or "").strip().upper()
        if not sym or sym in seen:
            continue
        name = str(row.get("name") or "")
        if is_junk_equity_symbol(sym, name=name):
            continue
        seen.add(sym)
        out.append(sym)
    out.sort()
    return out


def is_junk_equity_symbol(symbol: str, *, name: str = "") -> bool:
    """Heuristic: warrants / units / rights clutter the free-plan equity list."""
    sym = symbol.strip().upper()
    if not sym or "/" in sym:
        return True
    n = (name or "").lower()
    if any(tok in n for tok in ("warrant", " right", "rights", " unit", " units")):
        return True
    if sym.endswith(("WS", "WT", "WD", "RT")):
        return True
    # Long tickers ending in W/U/R are often structured products.
    if len(sym) >= 5 and "." not in sym and sym[-1] in "WUR":
        return True
    return False
