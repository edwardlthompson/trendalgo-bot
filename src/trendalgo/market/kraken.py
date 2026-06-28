"""Kraken public OHLCV via CCXT (no API key required)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from trendalgo.market.symbols import kraken_ccxt_pair
from trendalgo.market.types import OhlcvPoint, PricePoint

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
    sym = symbol.upper()
    if sym in KRAKEN_PAIR:
        return KRAKEN_PAIR[sym]
    return kraken_ccxt_pair(sym)


def _client() -> Any:
    import ccxt

    return ccxt.kraken({"enableRateLimit": True})


def _fetch_ohlcv_rows(
    symbol: str,
    timeframe: str,
    since: datetime,
    until: datetime,
    *,
    on_batch: Callable[[int, int], None] | None = None,
) -> list[list[float]]:
    if since.tzinfo is None:
        since = since.replace(tzinfo=UTC)
    if until.tzinfo is None:
        until = until.replace(tzinfo=UTC)
    pair = kraken_pair(symbol)
    since_ms = int(since.timestamp() * 1000)
    until_ms = int(until.timestamp() * 1000)
    exchange = _client()
    rows: list[list[float]] = []
    cursor = since_ms
    while cursor <= until_ms:
        batch = exchange.fetch_ohlcv(pair, timeframe, since=cursor, limit=720)
        if not batch:
            break
        rows.extend(batch)
        on_batch and on_batch(len(batch), len(rows))
        last_ms = int(batch[-1][0])
        if last_ms <= cursor:
            break
        cursor = last_ms + 1
        if len(batch) < 720:
            break
    return rows


def fetch_ohlcv(
    symbol: str,
    timeframe: str,
    since: datetime,
    until: datetime,
    *,
    on_batch: Callable[[int, int], None] | None = None,
) -> list[OhlcvPoint]:
    """Fetch OHLCV candles from Kraken between since and until (UTC)."""
    if since.tzinfo is None:
        since = since.replace(tzinfo=UTC)
    if until.tzinfo is None:
        until = until.replace(tzinfo=UTC)
    rows = _fetch_ohlcv_rows(symbol, timeframe, since, until, on_batch=on_batch)
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
    return [PricePoint(time=p.time, close=p.close) for p in fetch_ohlcv(symbol, timeframe, since, until)]
