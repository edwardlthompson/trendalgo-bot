"""Trading pair lists per exchange (ccxt with static fallback)."""

from __future__ import annotations

import os
import threading
import time
from typing import Any

from trendalgo.exchanges.registry import load_registry
from trendalgo.exchanges.static_kraken_usd import KRAKEN_USD_PAIRS

_STATIC: dict[str, list[str]] = {
    "kraken": list(KRAKEN_USD_PAIRS),
    "coinbase": [
        "BTC/USD",
        "ETH/USD",
        "SOL/USD",
        "AVAX/USD",
        "LINK/USD",
        "ADA/USD",
        "DOT/USD",
        "MATIC/USD",
        "UNI/USD",
        "LTC/USD",
    ],
    "binanceus": [
        "BTC/USD",
        "ETH/USD",
        "SOL/USD",
        "BNB/USD",
        "XRP/USD",
        "ADA/USD",
        "DOGE/USD",
        "AVAX/USD",
        "LINK/USD",
        "DOT/USD",
    ],
    "gemini": [
        "BTC/USD",
        "ETH/USD",
        "SOL/USD",
        "LTC/USD",
        "XRP/USD",
        "DOGE/USD",
        "AVAX/USD",
        "LINK/USD",
        "UNI/USD",
        "MATIC/USD",
    ],
}

_CACHE_LOCK = threading.Lock()
_CACHE: dict[str, tuple[float, list[str]]] = {}
_REFRESHING: set[str] = set()
_DEFAULT_TTL_S = 3600.0


def _ttl_s() -> float:
    raw = os.environ.get("TRENDALGO_PAIRS_CACHE_TTL_S", "").strip()
    if not raw:
        return _DEFAULT_TTL_S
    try:
        return max(0.0, float(raw))
    except ValueError:
        return _DEFAULT_TTL_S


def _static_pairs(exchange_id: str) -> list[str]:
    return sorted(_STATIC.get(exchange_id, list(KRAKEN_USD_PAIRS)))


def _fetch_live_pairs(exchange_id: str) -> list[str]:
    registry = load_registry()
    entry = registry.by_id(exchange_id)
    static = _static_pairs(exchange_id)
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


def _refresh_cache(exchange_id: str) -> None:
    try:
        pairs = _fetch_live_pairs(exchange_id)
        with _CACHE_LOCK:
            _CACHE[exchange_id] = (time.monotonic(), pairs)
    finally:
        with _CACHE_LOCK:
            _REFRESHING.discard(exchange_id)


def list_pairs_for_exchange(exchange_id: str, *, force_refresh: bool = False) -> list[str]:
    """Return USD pairs; serve cache/static immediately and refresh ccxt in background."""
    ttl = _ttl_s()
    now = time.monotonic()
    with _CACHE_LOCK:
        hit = _CACHE.get(exchange_id)
        if not force_refresh and hit is not None and ttl > 0 and (now - hit[0]) < ttl:
            return list(hit[1])
        stale_or_static = list(hit[1]) if hit is not None else _static_pairs(exchange_id)
        if force_refresh or ttl <= 0:
            pass
        elif exchange_id not in _REFRESHING:
            _REFRESHING.add(exchange_id)
            threading.Thread(
                target=_refresh_cache,
                args=(exchange_id,),
                name=f"pairs-refresh-{exchange_id}",
                daemon=True,
            ).start()
            return stale_or_static
        else:
            return stale_or_static

    pairs = _fetch_live_pairs(exchange_id)
    with _CACHE_LOCK:
        _CACHE[exchange_id] = (time.monotonic(), pairs)
    return list(pairs)
