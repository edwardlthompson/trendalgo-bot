"""Unified asset symbol normalization across exchanges (S14)."""

from __future__ import annotations

# Kraken-style prefixes and common exchange quirks
_ASSET_ALIASES: dict[str, str] = {
    "ZUSD": "USD",
    "XXBT": "BTC",
    "XBT": "BTC",
    "XETH": "ETH",
    "XLTC": "LTC",
    "XXRP": "XRP",
    "ZEUR": "EUR",
    "USDT": "USDT",
    "USD": "USD",
}


def normalize_asset(asset: str) -> str:
    """Map venue-specific asset codes to canonical symbols (e.g. ZUSD → USD)."""
    key = str(asset).upper()
    if key in _ASSET_ALIASES:
        return _ASSET_ALIASES[key]
    if key.startswith("Z") and len(key) == 4:
        return key[1:]
    return key


def normalize_holdings_assets(holdings: list[dict[str, object]]) -> list[dict[str, object]]:
    """Return holdings with normalized asset keys (for aggregation)."""
    out: list[dict[str, object]] = []
    for row in holdings:
        item = dict(row)
        item["asset"] = normalize_asset(str(row.get("asset", "")))
        out.append(item)
    return out
