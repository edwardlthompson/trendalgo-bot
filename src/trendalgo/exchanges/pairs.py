"""Trading pair lists per exchange (ccxt with static fallback)."""

from __future__ import annotations

from typing import Any

from trendalgo.exchanges.registry import load_registry
from trendalgo.exchanges.static_kraken_usd import KRAKEN_USD_PAIRS

_STATIC: dict[str, list[str]] = {
    "kraken": list(KRAKEN_USD_PAIRS),
    "coinbase": ["BTC/USD", "ETH/USD", "SOL/USD", "AVAX/USD", "LINK/USD", "ADA/USD", "DOT/USD", "MATIC/USD", "UNI/USD", "LTC/USD"],
    "binanceus": ["BTC/USD", "ETH/USD", "SOL/USD", "BNB/USD", "XRP/USD", "ADA/USD", "DOGE/USD", "AVAX/USD", "LINK/USD", "DOT/USD"],
    "gemini": ["BTC/USD", "ETH/USD", "SOL/USD", "LTC/USD", "XRP/USD", "DOGE/USD", "AVAX/USD", "LINK/USD", "UNI/USD", "MATIC/USD"],
}


def list_pairs_for_exchange(exchange_id: str) -> list[str]:
    registry = load_registry()
    entry = registry.by_id(exchange_id)
    static = sorted(_STATIC.get(exchange_id, list(KRAKEN_USD_PAIRS)))
    if entry is None:
        return static
    try:
        import ccxt

        exchange_class = getattr(ccxt, entry.ccxt_id, None)
        if exchange_class is None:
            raise ValueError("unknown ccxt class")
        client = exchange_class({"enableRateLimit": True})
        markets: dict[str, Any] = client.load_markets()
        quotes = set(entry.usd_aliases)
        pairs: list[str] = []
        for symbol, meta in markets.items():
            if not meta.get("active", True):
                continue
            quote = str(meta.get("quote", ""))
            if quote not in quotes and not symbol.endswith("/USD"):
                continue
            base = str(meta.get("base", symbol.split("/")[0]))
            normalized = f"{base}/USD"
            if normalized not in pairs:
                pairs.append(normalized)
        if len(pairs) >= 10:
            return sorted(pairs)
    except Exception:
        pass
    return static
