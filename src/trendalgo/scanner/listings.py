"""Kraken spot listing verification (O2) — public markets, no API keys.

Universe is one canonical pair per base across all active Kraken spot quotes
(USD preferred, then USDT, USDC, EUR, then other). Volume gates still use
Kraken venue notional — not CoinMarketCap global volume.
"""

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

# Lower rank = preferred quote for candles / backtests.
_QUOTE_RANK: dict[str, int] = {
    "USD": 0,
    "ZUSD": 0,
    "USDT": 1,
    "USDC": 2,
    "EUR": 3,
    "GBP": 4,
    "AUD": 5,
    "CAD": 6,
    "JPY": 7,
    "CHF": 8,
    "BTC": 20,
    "ETH": 21,
    "SOL": 22,
}

# Fiat / cash bases are not scanner "coins" (EUR/USD etc.).
_SKIP_BASES = frozenset(
    {
        "USD",
        "ZUSD",
        "EUR",
        "GBP",
        "JPY",
        "CAD",
        "AUD",
        "CHF",
        "USDT",
        "USDC",
        "DAI",
        "EURC",
        "USD1",
    }
)

_LOG = logging.getLogger(__name__)
_CACHE: tuple[float, list[str]] | None = None
_CACHE_TTL_SEC = 3600.0


def _normalize_pair(symbol: str) -> str | None:
    """Legacy explicit-pair path: USDT quote → USD label."""
    if "/" not in symbol:
        return None
    return symbol.upper().replace("USDT", "USD")


def _format_pair(base: str, quote: str) -> str:
    b = base.strip().upper()
    q = quote.strip().upper()
    if q == "ZUSD":
        q = "USD"
    return f"{b}/{q}"


def _quote_rank(quote: str) -> int:
    return _QUOTE_RANK.get(quote.strip().upper(), 50)


def pick_canonical_pair(candidates: list[str]) -> str | None:
    """Among BASE/QUOTE strings for one base, prefer USD > USDT > USDC > EUR > other."""
    best: str | None = None
    best_rank = 10_000
    for raw in candidates:
        if "/" not in raw:
            continue
        base, quote = raw.upper().split("/", 1)
        if not base or base in _SKIP_BASES:
            continue
        pair = _format_pair(base, quote)
        rank = _quote_rank(quote)
        if best is None or rank < best_rank or (rank == best_rank and pair < best):
            best = pair
            best_rank = rank
    return best


def _fetch_kraken_spot_canonical() -> list[str]:
    """One canonical active spot pair per base (all quotes considered)."""
    import ccxt

    exchange = ccxt.kraken({"enableRateLimit": True, "timeout": 10_000})
    markets: dict[str, Any] = exchange.load_markets()
    by_base: dict[str, list[str]] = {}
    for symbol, market in markets.items():
        if not market.get("spot", True):
            continue
        if market.get("active") is False:
            continue
        base = str(market.get("base") or "").upper()
        quote = str(market.get("quote") or "").upper()
        if not base or not quote or base in _SKIP_BASES:
            continue
        if "/" in symbol:
            pair = symbol.upper()
        else:
            pair = _format_pair(base, quote)
        by_base.setdefault(base, []).append(pair)
    out: list[str] = []
    for base in sorted(by_base):
        chosen = pick_canonical_pair(by_base[base])
        if chosen:
            out.append(chosen)
    return out


# Back-compat alias for tests/monkeypatches.
def _fetch_kraken_usd_spot() -> list[str]:
    return _fetch_kraken_spot_canonical()


def verify_kraken_listings(pairs: tuple[str, ...] | None = None) -> list[str]:
    """Return canonical Kraken spot pairs (live public markets or fallback)."""
    if pairs is not None:
        return [p for p in (_normalize_pair(x) for x in pairs) if p]

    if os.environ.get("TRENDALGO_MARKET_SOURCE", "").lower() == "synthetic":
        return list(DEFAULT_KRAKEN_SPOT)

    global _CACHE
    now = time.monotonic()
    if _CACHE is not None and (now - _CACHE[0]) < _CACHE_TTL_SEC:
        return list(_CACHE[1])

    try:
        live = _fetch_kraken_spot_canonical()
        if len(live) < 5:
            raise RuntimeError("kraken markets returned too few spot pairs")
        # Full Kraken spot catalog (one pair per base). Optional cap:
        # TRENDALGO_SCANNER_MAX_PAIRS (0 / unset = no cap).
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
