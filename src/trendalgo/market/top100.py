"""Top-100 crypto universe from CoinGecko (free public API)."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass

_COINGECKO_MARKETS = (
    "https://api.coingecko.com/api/v3/coins/markets"
    "?vs_currency=usd&order=market_cap_desc&per_page=100&page=1&sparkline=false"
)


@dataclass(frozen=True)
class Top100Asset:
    symbol: str
    name: str
    price_usd: float
    market_cap_rank: int


def fetch_top100_universe(*, timeout_sec: float = 30.0) -> list[Top100Asset]:
    """Return top-100 assets by market cap with live USD prices."""
    req = urllib.request.Request(
        _COINGECKO_MARKETS,
        headers={"Accept": "application/json", "User-Agent": "TrendAlgo-Bot/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            rows = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise RuntimeError(f"CoinGecko top-100 fetch failed: {exc}") from exc
    assets: list[Top100Asset] = []
    for row in rows:
        price = float(row.get("current_price") or 0)
        if price <= 0:
            continue
        assets.append(
            Top100Asset(
                symbol=str(row.get("symbol", "")).upper(),
                name=str(row.get("name", "")),
                price_usd=price,
                market_cap_rank=int(row.get("market_cap_rank") or 0),
            )
        )
    if len(assets) < 50:
        raise RuntimeError(f"CoinGecko returned too few assets: {len(assets)}")
    return assets
