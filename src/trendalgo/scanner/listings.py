"""Kraken spot listing verification (O2) — public markets, no API keys."""

from __future__ import annotations

import logging
import os
import time
from typing import Any

DEFAULT_KRAKEN_SPOT = (
    "BTC/USD",
    "ETH/USD",
    "SOL/USD",
    "ADA/USD",
    "DOT/USD",
    "XRP/USD",
    "LINK/USD",
    "AVAX/USD",
    "DOGE/USD",
    "BNB/USD",
)

_LOG = logging.getLogger(__name__)
_CACHE: tuple[float, list[str]] | None = None
_CACHE_TTL_SEC = 3600.0


def _normalize_pair(symbol: str) -> str | None:
    if "/" not in symbol:
        return None
    return symbol.upper().replace("USDT", "USD")


def _fetch_kraken_usd_spot() -> list[str]:
    import ccxt

    exchange = ccxt.kraken({"enableRateLimit": True, "timeout": 10_000})
    markets: dict[str, Any] = exchange.load_markets()
    pairs: list[str] = []
    for symbol, market in markets.items():
        if not market.get("spot", True):
            continue
        if market.get("active") is False:
            continue
        quote = str(market.get("quote") or "").upper()
        if quote not in {"USD", "ZUSD"}:
            continue
        # Prefer USD quote symbols (skip EUR/GBP/etc.)
        norm = _normalize_pair(symbol)
        if norm and norm.endswith("/USD"):
            pairs.append(norm)
    # Dedupe preserve order
    seen: set[str] = set()
    out: list[str] = []
    for p in pairs:
        if p not in seen:
            seen.add(p)
            out.append(p)
    out.sort()
    return out


def verify_kraken_listings(pairs: tuple[str, ...] | None = None) -> list[str]:
    """Return normalized Kraken USD spot pairs (live public markets or fallback)."""
    if pairs is not None:
        return [p for p in (_normalize_pair(x) for x in pairs) if p]

    if os.environ.get("TRENDALGO_MARKET_SOURCE", "").lower() == "synthetic":
        return list(DEFAULT_KRAKEN_SPOT)

    global _CACHE
    now = time.monotonic()
    if _CACHE is not None and (now - _CACHE[0]) < _CACHE_TTL_SEC:
        return list(_CACHE[1])

    try:
        live = _fetch_kraken_usd_spot()
        if len(live) < 5:
            raise RuntimeError("kraken markets returned too few USD spot pairs")
        # Full Kraken USD spot catalog (not the 10-pair curated demo set).
        # Optional cap: TRENDALGO_SCANNER_MAX_PAIRS (0 / unset = no cap).
        universe = list(live)
        raw_cap = os.environ.get("TRENDALGO_SCANNER_MAX_PAIRS", "").strip()
        if raw_cap:
            try:
                cap = int(raw_cap)
            except ValueError:
                cap = 0
            if cap > 0:
                universe = universe[:cap]
        _CACHE = (now, universe)
        return list(universe)
    except Exception as exc:
        _LOG.warning("Kraken listings fetch failed (%s); using default universe", exc)
        return list(DEFAULT_KRAKEN_SPOT)
