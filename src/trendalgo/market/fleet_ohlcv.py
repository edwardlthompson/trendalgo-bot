"""Fleet backtest OHLCV gating — only timeframes available from free exchange candles."""

from __future__ import annotations

import os
from collections.abc import Callable
from datetime import datetime
from functools import lru_cache
from typing import Any

from trendalgo.constants.timeframes import (
    TRADINGVIEW_INTERVALS,
    ccxt_interval_seconds,
    timeframe_for_fetch,
)
from trendalgo.market.service import OnOhlcvProgress, PriceHistoryService
from trendalgo.market.types import OhlcvPoint

MIN_FLEET_OHLCV_BARS = 50
LOOKBACK_COVERAGE_RATIO = 0.90
KRAKEN_MAX_OHLCV_BARS = 720


def market_uses_synthetic() -> bool:
    return os.environ.get("TRENDALGO_MARKET_SOURCE", "kraken").lower() == "synthetic"


@lru_cache(maxsize=8)
def list_exchange_fetch_timeframes(exchange_id: str) -> tuple[str, ...]:
    """CCXT fetch intervals supported by the exchange, coarsest to finest."""
    import ccxt

    ex_id = exchange_id.lower().strip()
    if not hasattr(ccxt, ex_id):
        return ("1h", "1d")
    exchange: Any = getattr(ccxt, ex_id)({"enableRateLimit": True})
    exchange.load_markets()
    frames = getattr(exchange, "timeframes", None) or {}
    if not frames:
        return ("1h", "1d")
    return tuple(sorted(frames.keys(), key=ccxt_interval_seconds))


def finest_exchange_fetch_timeframe(exchange_id: str) -> str:
    supported = list_exchange_fetch_timeframes(exchange_id)
    return supported[0] if supported else "1h"


def min_fetch_seconds_for_lookback(
    lookback_seconds: int,
    *,
    max_bars: int = KRAKEN_MAX_OHLCV_BARS,
) -> int:
    """Smallest bar size that can span the lookback within one paginated series."""
    need = int(lookback_seconds * LOOKBACK_COVERAGE_RATIO)
    return max(60, (need + max_bars - 1) // max_bars)


def resolve_finest_fetch_timeframe(
    exchange_id: str,
    lookback_seconds: int,
) -> str:
    """Pick finest exchange interval that can cover the lookback (Kraken: 720 bars max)."""
    min_sec = min_fetch_seconds_for_lookback(lookback_seconds)
    for fetch_tf in list_exchange_fetch_timeframes(exchange_id):
        if ccxt_interval_seconds(fetch_tf) >= min_sec:
            return fetch_tf
    supported = list_exchange_fetch_timeframes(exchange_id)
    return supported[-1] if supported else "1h"


def select_tv_timeframes_for_exchange(
    exchange_id: str,
    *,
    min_fetch_timeframe: str | None = None,
) -> tuple[str, ...]:
    """TradingView intervals whose CCXT fetch TF is supported and not finer than min."""
    supported = set(list_exchange_fetch_timeframes(exchange_id))
    min_sec = ccxt_interval_seconds(min_fetch_timeframe) if min_fetch_timeframe else 0
    out: list[str] = []
    for tv in TRADINGVIEW_INTERVALS:
        fetch_tf = timeframe_for_fetch(tv)
        if fetch_tf not in supported:
            continue
        if ccxt_interval_seconds(fetch_tf) < min_sec:
            continue
        out.append(tv)
    return tuple(out)


def _bar_span_seconds(points: list[OhlcvPoint]) -> int:
    if len(points) < 2:
        return 0
    return int(points[-1].time - points[0].time)


def min_bars_for_fetch_timeframe(
    fetch_tf: str,
    since: datetime,
    until: datetime,
) -> int:
    step = ccxt_interval_seconds(fetch_tf)
    expected = max(2, int((until - since).total_seconds() / max(step, 1)))
    return max(2, min(MIN_FLEET_OHLCV_BARS, int(expected * LOOKBACK_COVERAGE_RATIO)))


def ohlcv_covers_lookback(
    points: list[OhlcvPoint],
    since: datetime,
    until: datetime,
    *,
    fetch_tf: str,
) -> bool:
    min_bars = min_bars_for_fetch_timeframe(fetch_tf, since, until)
    if len(points) < min_bars:
        return False
    need = int((until - since).total_seconds() * LOOKBACK_COVERAGE_RATIO)
    return _bar_span_seconds(points) >= need


def prefetch_fleet_ohlcv(
    market: PriceHistoryService,
    exchange_id: str,
    pair: str,
    since: datetime,
    until: datetime,
    *,
    on_progress: OnOhlcvProgress | None = None,
    on_log: Callable[[str], None] | None = None,
) -> tuple[str, int]:
    """Download the finest free OHLCV series that can cover the lookback window."""
    lookback = int((until - since).total_seconds())
    fetch_tf = resolve_finest_fetch_timeframe(exchange_id, lookback)
    on_progress and on_progress(
        "prefetch",
        f"Downloading {exchange_id} {pair} {fetch_tf} for {lookback // 86_400}d lookback…",
    )
    points = market.get_ohlcv(
        pair,
        fetch_tf,
        since,
        until,
        exchange_id=exchange_id,
        on_progress=on_progress,
    )
    span_days = _bar_span_seconds(points) / 86_400 if points else 0.0
    if not ohlcv_covers_lookback(points, since, until, fetch_tf=fetch_tf):
        msg = (
            f"OHLCV {exchange_id} {pair} {fetch_tf} insufficient: "
            f"{len(points)} bars / {span_days:.1f}d span"
        )
        raise ValueError(msg)
    on_log and on_log(
        f"Finest interval covering lookback: {fetch_tf} ({len(points):,} bars, {span_days:.1f}d span)"
    )
    return fetch_tf, len(points)


def prefetch_eligible_timeframes(
    market: PriceHistoryService,
    exchange_id: str,
    pair: str,
    since: datetime,
    until: datetime,
    tv_timeframes: tuple[str, ...],
    *,
    on_progress: OnOhlcvProgress | None = None,
) -> dict[str, int]:
    """Warm cache for each eligible TV interval; return {tv: bar_count}."""
    counts: dict[str, int] = {}
    for tv in tv_timeframes:
        fetch_tf = timeframe_for_fetch(tv)
        on_progress and on_progress("prefetch", f"Prefetch {exchange_id} {pair} {tv} ({fetch_tf})…")
        points = market.get_ohlcv(
            pair,
            fetch_tf,
            since,
            until,
            exchange_id=exchange_id,
            on_progress=on_progress,
        )
        counts[tv] = len(points)
    return counts


def resolve_fleet_timeframes(
    market: PriceHistoryService,
    exchange_id: str,
    pair: str,
    since: datetime,
    until: datetime,
    requested: tuple[str, ...] | None,
    *,
    on_progress: OnOhlcvProgress | None = None,
    on_log: Callable[[str], None] | None = None,
) -> tuple[str, ...]:
    """Pick fleet TFs from free OHLCV; exclude intervals finer than the lookback allows."""
    if market_uses_synthetic():
        return requested or TRADINGVIEW_INTERVALS

    finest, finest_bars = prefetch_fleet_ohlcv(
        market,
        exchange_id,
        pair,
        since,
        until,
        on_progress=on_progress,
        on_log=on_log,
    )
    if finest_bars < 2:
        raise ValueError(f"Insufficient OHLCV for {exchange_id} {pair} at {finest}")

    gated = select_tv_timeframes_for_exchange(exchange_id, min_fetch_timeframe=finest)
    if requested:
        allowed = set(gated)
        gated = tuple(tf for tf in requested if tf in allowed)

    on_log and on_log(
        f"OHLCV gate: floor {finest} ({finest_bars:,} bars); "
        f"candidate timeframes: {', '.join(gated)}"
    )

    counts = prefetch_eligible_timeframes(
        market,
        exchange_id,
        pair,
        since,
        until,
        gated,
        on_progress=on_progress,
    )
    usable: list[str] = []
    for tv in gated:
        fetch_tf = timeframe_for_fetch(tv)
        points = market.get_ohlcv(
            pair,
            fetch_tf,
            since,
            until,
            exchange_id=exchange_id,
        )
        if ohlcv_covers_lookback(points, since, until, fetch_tf=fetch_tf):
            usable.append(tv)
    skipped = [tf for tf in gated if tf not in usable]
    if skipped:
        on_log and on_log(
            f"Skipped timeframes with insufficient OHLCV: {', '.join(skipped)} "
            f"(counts: {', '.join(f'{tf}={counts.get(tf, 0)}' for tf in skipped)})"
        )
    if not usable:
        raise ValueError(f"No usable OHLCV timeframes for {exchange_id} {pair}")
    on_log and on_log(f"Testing {len(usable)} timeframes: {', '.join(usable)}")
    return tuple(usable)
