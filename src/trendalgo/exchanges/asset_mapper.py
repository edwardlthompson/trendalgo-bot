"""Unified asset symbol normalization across exchanges (S14)."""

from __future__ import annotations

# Kraken-style prefixes and common exchange quirks
_ASSET_ALIASES: dict[str, str] = {
    "ZUSD": "USD",
    "ZGBP": "GBP",
    "ZCAD": "CAD",
    "ZJPY": "JPY",
    "ZAUD": "AUD",
    "ZEUR": "EUR",
    "XXBT": "BTC",
    "XBT": "BTC",
    "XETH": "ETH",
    "ETH2": "ETH",
    "XLTC": "LTC",
    "XXRP": "XRP",
    "XXDG": "DOGE",
    "XDG": "DOGE",
    "XETC": "ETC",
    "XMLN": "MLN",
    "XREP": "REP",
    "XXLM": "XLM",
    "XXMR": "XMR",
    "XZEC": "ZEC",
    "USDT": "USDT",
    "USD": "USD",
}

_STAKING_SUFFIXES = (".S", ".M", ".F", ".P", ".B")


def normalize_asset(asset: str) -> str:
    """Map venue-specific asset codes to canonical symbols (e.g. ZUSD → USD, SOL.S → SOL)."""
    key = str(asset).strip().upper()
    for suffix in _STAKING_SUFFIXES:
        if key.endswith(suffix) and len(key) > len(suffix):
            key = key[: -len(suffix)]
            break
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
