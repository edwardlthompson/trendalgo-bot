"""Kraken public OHLCV via CCXT (no API key required)."""

from __future__ import annotations

import functools
import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from trendalgo.exchanges.pair_normalizer import normalize_pair
from trendalgo.market.rate_budget import call_with_backoff
from trendalgo.market.types import OhlcvPoint, PricePoint

# The plan's ten symbols. Each value equals normalize_pair(symbol, "kraken") (E4, tested).
KRAKEN_PAIR: dict[str, str] = {
    "BTC": "BTC/USD",
    "ETH": "ETH/USD",
    "SOL": "SOL/USD",
    "BNB": "BNB/USD",
    "XRP": "XRP/USD",
    "ADA": "ADA/USD",
    "DOGE": "DOGE/USD",
    "AVAX": "AVAX/USD",
    "DOT": "DOT/USD",
    "LINK": "LINK/USD",
}


def kraken_pair(symbol: str) -> str:
    """The Kraken pair for a symbol. Candles and orders use this one mapping (E4)."""
    return normalize_pair(symbol, "kraken")


def resolve_kraken_market(symbol: str) -> str:
    """Use an explicit BASE/QUOTE as-is; bare bases still map to venue USD."""
    raw = symbol.strip().upper()
    if "/" in raw:
        return raw
    return kraken_pair(raw)


# Quotes already priced near USD (treat quoteVolume as USD notional).
_USD_QUOTES = frozenset({"USD", "ZUSD", "USDT", "USDC", "DAI", "USD1", "EURC"})


def _rate_limit_errors() -> tuple[type[BaseException], ...]:
    import ccxt

    # RateLimitExceeded is not a DDoSProtection subclass in ccxt, so both are listed.
    return (ccxt.RateLimitExceeded, ccxt.DDoSProtection)


def _client(timeout_ms: int = 10_000) -> Any:
    import ccxt

    return ccxt.kraken({"enableRateLimit": True, "timeout": timeout_ms})


def _fetch_ohlcv_rows(
    symbol: str,
    timeframe: str,
    since: datetime,
    until: datetime,
    *,
    on_batch: Callable[[int, int], None] | None = None,
    timeout_ms: int = 10_000,
) -> list[list[float]]:
    if since.tzinfo is None:
        since = since.replace(tzinfo=UTC)
    if until.tzinfo is None:
        until = until.replace(tzinfo=UTC)
    pair = resolve_kraken_market(symbol)
    since_ms = int(since.timestamp() * 1000)
    until_ms = int(until.timestamp() * 1000)
    exchange = _client(timeout_ms)
    rows: list[list[float]] = []
    cursor = since_ms
    while cursor <= until_ms:
        batch = call_with_backoff(
            functools.partial(exchange.fetch_ohlcv, pair, timeframe, since=cursor, limit=720),
            retry_on=_rate_limit_errors(),
            sleep=time.sleep,
        )
        if not batch:
            break
        rows.extend(batch)
        on_batch and on_batch(len(batch), len(rows))
        last_ms = int(batch[-1][0])
        if last_ms >= until_ms:
            break
        next_cursor = last_ms + 1
        if next_cursor <= cursor:
            break
        cursor = next_cursor
    return rows


def _ticker_quote_notional(ticker: dict[str, Any]) -> float | None:
    quote = ticker.get("quoteVolume")
    if quote is None:
        last = ticker.get("last") or ticker.get("close")
        base_vol = ticker.get("baseVolume")
        if last is not None and base_vol is not None:
            try:
                return float(last) * float(base_vol)
            except (TypeError, ValueError):
                return None
    try:
        return float(quote) if quote is not None else None
    except (TypeError, ValueError):
        return None


def _usd_fx_rates(raw: dict[str, Any]) -> dict[str, float]:
    """Map quote currency → USD multiplier (how many USD per 1 unit of quote)."""
    rates: dict[str, float] = {q: 1.0 for q in _USD_QUOTES}

    def _last(sym: str) -> float | None:
        ticker = raw.get(sym)
        if not isinstance(ticker, dict):
            return None
        last = ticker.get("last") or ticker.get("close")
        try:
            value = float(last) if last is not None else None
        except (TypeError, ValueError):
            return None
        return value if value and value > 0 else None

    for quote, usd_pair in (
        ("EUR", "EUR/USD"),
        ("GBP", "GBP/USD"),
        ("AUD", "AUD/USD"),
        ("CAD", "CAD/USD"),
        ("CHF", "CHF/USD"),
        ("JPY", "USD/JPY"),
    ):
        last = _last(usd_pair)
        if last is None:
            continue
        # USD/JPY is inverted (JPY per USD).
        rates[quote] = (1.0 / last) if quote == "JPY" else last

    btc_usd = _last("BTC/USD")
    if btc_usd:
        rates["BTC"] = btc_usd
        rates["XBT"] = btc_usd
    eth_usd = _last("ETH/USD")
    if eth_usd:
        rates["ETH"] = eth_usd
    sol_usd = _last("SOL/USD")
    if sol_usd:
        rates["SOL"] = sol_usd
    return rates


def _aggregate_base_volumes_usd(raw: dict[str, Any]) -> dict[str, float]:
    """Sum 24h USD notional per base across all Kraken spot tickers."""
    rates = _usd_fx_rates(raw)
    by_base: dict[str, float] = {}
    for symbol, ticker in raw.items():
        if not isinstance(ticker, dict) or "/" not in symbol:
            continue
        base, quote = symbol.upper().split("/", 1)
        if not base:
            continue
        notional = _ticker_quote_notional(ticker)
        if notional is None or notional <= 0:
            continue
        fx = rates.get(quote)
        if fx is None:
            # Unknown quote: skip rather than treat quoteVolume as USD.
            continue
        by_base[base] = by_base.get(base, 0.0) + float(notional) * float(fx)
    return by_base


def fetch_quote_volumes(
    pairs: list[str],
    *,
    timeout_ms: int = 10_000,
) -> dict[str, float]:
    """24h USD notional per canonical pair = sum of that base's Kraken spot markets.

    Venue volume only (not CoinMarketCap global). Cheap prefilter before OHLCV.
    """
    if not pairs:
        return {}
    client = _client(timeout_ms=timeout_ms)
    raw = call_with_backoff(
        client.fetch_tickers,
        retry_on=_rate_limit_errors(),
        sleep=time.sleep,
    )
    if not isinstance(raw, dict):
        return {}
    by_base = _aggregate_base_volumes_usd(raw)
    out: dict[str, float] = {}
    for pair in pairs:
        base = pair.split("/", 1)[0].upper() if "/" in pair else pair.upper()
        if base in by_base:
            out[pair] = by_base[base]
    return out


def fetch_ohlcv(
    symbol: str,
    timeframe: str,
    since: datetime,
    until: datetime,
    *,
    on_batch: Callable[[int, int], None] | None = None,
    timeout_ms: int = 10_000,
) -> list[OhlcvPoint]:
    """Fetch OHLCV candles from Kraken between since and until (UTC)."""
    if since.tzinfo is None:
        since = since.replace(tzinfo=UTC)
    if until.tzinfo is None:
        until = until.replace(tzinfo=UTC)
    rows = _fetch_ohlcv_rows(
        symbol, timeframe, since, until, on_batch=on_batch, timeout_ms=timeout_ms
    )
    points: list[OhlcvPoint] = []
    seen: set[int] = set()
    for row in rows:
        ts_sec = int(row[0] // 1000)
        if ts_sec < int(since.timestamp()) or ts_sec > int(until.timestamp()):
            continue
        if ts_sec in seen:
            continue
        seen.add(ts_sec)
        points.append(
            OhlcvPoint(
                time=ts_sec,
                open=float(row[1]),
                high=float(row[2]),
                low=float(row[3]),
                close=float(row[4]),
                volume=float(row[5]),
            )
        )
    points.sort(key=lambda p: p.time)
    return points


def fetch_closes(
    symbol: str,
    timeframe: str,
    since: datetime,
    until: datetime,
) -> list[PricePoint]:
    """Fetch close prices from Kraken between since and until (UTC)."""
    return [
        PricePoint(time=p.time, close=p.close) for p in fetch_ohlcv(symbol, timeframe, since, until)
    ]
