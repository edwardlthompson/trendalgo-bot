"""Market price history with Kraken fetch + SQLite cache."""

from __future__ import annotations

import os
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

from trendalgo.constants.timeframes import ccxt_interval_seconds
from trendalgo.market.cache import PriceCache
from trendalgo.market.ccxt_ohlcv import fetch_exchange_ohlcv
from trendalgo.market.kraken import fetch_closes
from trendalgo.market.kraken import fetch_ohlcv as fetch_kraken_ohlcv
from trendalgo.market.ohlcv_cache import OhlcvCache
from trendalgo.market.symbols import base_symbol
from trendalgo.market.synthetic import synthetic_ohlcv, synthetic_series
from trendalgo.market.types import OhlcvPoint, PricePoint

_SOURCE = "kraken"
HOURLY_RANGES = frozenset({"14d", "7d", "24h"})
DAILY_RANGES = frozenset({"1y", "6m", "3m", "1m"})

OnOhlcvProgress = Callable[[str, str], None]


def range_window(range_key: str) -> timedelta:
    mapping = {
        "1y": timedelta(days=365),
        "6m": timedelta(days=182),
        "3m": timedelta(days=91),
        "1m": timedelta(days=30),
        "14d": timedelta(days=14),
        "7d": timedelta(days=7),
        "24h": timedelta(hours=24),
    }
    return mapping[range_key]


def granularity_for_range(range_key: str) -> str:
    return "1h" if range_key in HOURLY_RANGES else "1d"


def _use_synthetic() -> bool:
    return os.environ.get("TRENDALGO_MARKET_SOURCE", "kraken").lower() == "synthetic"


class PriceHistoryService:
    def __init__(self, cache_path: Path) -> None:
        self._cache = PriceCache(cache_path)
        self._ohlcv = OhlcvCache(cache_path.parent / "ohlcv_prices.db")

    def ohlcv_cache_count(
        self,
        symbol: str,
        timeframe: str,
        since: datetime,
        until: datetime,
    ) -> int:
        sym = base_symbol(symbol).upper()
        return self._ohlcv.count_in_range(_SOURCE, sym, timeframe, since, until)

    def get_closes(
        self,
        symbol: str,
        timeframe: str,
        since: datetime,
        until: datetime,
    ) -> list[PricePoint]:
        sym = base_symbol(symbol)
        if _use_synthetic():
            return synthetic_series(sym, timeframe, since, until)
        cached = self._cache.query(_SOURCE, sym.upper(), timeframe, since, until)
        if _covers_window(cached, since, until, timeframe):
            return cached
        try:
            fresh = fetch_closes(symbol, timeframe, since, until)
        except Exception:
            if cached:
                return cached
            return synthetic_series(sym, timeframe, since, until)
        self._cache.upsert(_SOURCE, sym.upper(), timeframe, fresh)
        merged = self._cache.query(_SOURCE, sym.upper(), timeframe, since, until)
        return merged or fresh

    def get_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        since: datetime,
        until: datetime,
        *,
        exchange_id: str = "kraken",
        on_progress: OnOhlcvProgress | None = None,
    ) -> list[OhlcvPoint]:
        sym = base_symbol(symbol)
        sym_key = sym.upper()
        source = exchange_id.lower()
        if _use_synthetic():
            return synthetic_ohlcv(sym, timeframe, since, until)
        cached = self._ohlcv.query(source, sym_key, timeframe, since, until)
        if _covers_ohlcv_window(cached, since, until, timeframe):
            on_progress and on_progress(
                "cache_hit",
                f"Cache hit: {len(cached):,} bars for {source} {symbol} {timeframe}",
            )
            return cached

        fetch_since = since
        if cached:
            step = ccxt_interval_seconds(timeframe)
            latest = cached[-1].time
            since_ts = int(since.replace(tzinfo=UTC).timestamp())
            if latest >= since_ts:
                fetch_since = datetime.fromtimestamp(latest + step, tz=UTC)
                on_progress and on_progress(
                    "incremental",
                    f"Incremental fetch: {len(cached):,} bars cached for {source}",
                )

        fresh: list[OhlcvPoint] = []
        if fetch_since <= until:
            try:
                on_progress and on_progress(
                    "fetch_start",
                    f"Downloading OHLCV {source} {symbol} {timeframe}…",
                )

                def batch_cb(batch_size: int, total: int) -> None:
                    on_progress and on_progress(
                        "batch",
                        f"Received {batch_size} candles ({total:,} total) {source} {symbol}",
                    )

                if source == "kraken":
                    fresh = fetch_kraken_ohlcv(
                        symbol, timeframe, fetch_since, until, on_batch=batch_cb
                    )
                else:
                    fresh = fetch_exchange_ohlcv(
                        source, symbol, timeframe, fetch_since, until, on_batch=batch_cb
                    )
            except Exception as exc:
                on_progress and on_progress("error", f"Download error {source} {symbol}: {exc}")
                if cached:
                    return cached
                return synthetic_ohlcv(sym, timeframe, since, until)
            if fresh:
                self._ohlcv.upsert(source, sym_key, timeframe, fresh)
                on_progress and on_progress(
                    "downloaded",
                    f"{len(fresh):,} new bars saved for {source} {symbol} {timeframe}",
                )
        merged = self._ohlcv.query(source, sym_key, timeframe, since, until)
        return merged or cached or fresh


def _covers_ohlcv_window(
    points: list[OhlcvPoint],
    since: datetime,
    until: datetime,
    timeframe: str,
) -> bool:
    closes = [PricePoint(time=p.time, close=p.close) for p in points]
    return _covers_window(closes, since, until, timeframe)


def _covers_window(
    points: list[PricePoint],
    since: datetime,
    until: datetime,
    timeframe: str,
) -> bool:
    if len(points) < 2:
        return False
    step = ccxt_interval_seconds(timeframe)
    since_ts = int(since.replace(tzinfo=UTC).timestamp())
    until_ts = int(until.replace(tzinfo=UTC).timestamp())
    expected = max(2, (until_ts - since_ts) // max(step, 1))
    if len(points) < max(2, int(expected * 0.85)):
        return False
    return points[0].time <= since_ts + step and points[-1].time >= until_ts - step


_service: PriceHistoryService | None = None


def get_price_history_service(data_dir: Path | None = None) -> PriceHistoryService:
    global _service
    if _service is None:
        root = data_dir or Path(os.environ.get("TRENDALGO_DATA_DIR", "data"))
        _service = PriceHistoryService(root / "market_prices.db")
    return _service


def reset_price_history_service() -> None:
    global _service
    _service = None
