"""Generic CCXT OHLCV fetch for any registry exchange."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any, Callable

from trendalgo.exchanges.pair_normalizer import normalize_pair
from trendalgo.exchanges.registry import get_entry
from trendalgo.market.types import OhlcvPoint

BatchCallback = Callable[[int, int], None]


def _client(exchange_id: str) -> Any:
    import ccxt

    entry = get_entry(exchange_id)
    exchange_class = getattr(ccxt, entry.ccxt_id, None)
    if exchange_class is None:
        raise ValueError(f"ccxt has no exchange class: {entry.ccxt_id}")
    return exchange_class({"enableRateLimit": True})


def fetch_exchange_ohlcv(
    exchange_id: str,
    pair: str,
    timeframe: str,
    since: datetime,
    until: datetime,
    *,
    on_batch: BatchCallback | None = None,
    max_retries: int = 3,
) -> list[OhlcvPoint]:
    if since.tzinfo is None:
        since = since.replace(tzinfo=UTC)
    if until.tzinfo is None:
        until = until.replace(tzinfo=UTC)
    ccxt_pair = normalize_pair(pair, exchange_id)
    since_ms = int(since.timestamp() * 1000)
    until_ms = int(until.timestamp() * 1000)
    delay = 1.0
    last_exc: Exception | None = None

    for attempt in range(max_retries):
        try:
            exchange = _client(exchange_id)
            rows: list[list[float]] = []
            cursor = since_ms
            while cursor <= until_ms:
                batch = exchange.fetch_ohlcv(ccxt_pair, timeframe, since=cursor, limit=720)
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
            return _rows_to_points(rows, since, until)
        except Exception as exc:
            last_exc = exc
            if attempt + 1 >= max_retries:
                break
            time.sleep(delay)
            delay *= 2.0
    raise last_exc or RuntimeError("OHLCV fetch failed")


def _rows_to_points(
    rows: list[list[float]],
    since: datetime,
    until: datetime,
) -> list[OhlcvPoint]:
    since_ts = int(since.timestamp())
    until_ts = int(until.timestamp())
    points: list[OhlcvPoint] = []
    seen: set[int] = set()
    for row in rows:
        ts_sec = int(row[0] // 1000)
        if ts_sec < since_ts or ts_sec > until_ts or ts_sec in seen:
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
