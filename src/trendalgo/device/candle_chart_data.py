"""OHLC windowing and trade marker points for the backtest candle chart (pure, no Qt)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

import pandas as pd

DEFAULT_PAD_BARS = 12
DEFAULT_MAX_BARS = 280


@dataclass(frozen=True)
class OhlcBar:
    ms: int
    open: float
    high: float
    low: float
    close: float


@dataclass(frozen=True)
class TradeMarker:
    ms: int
    price: float


def timestamp_ms(raw: object) -> int | None:
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        ts = pd.Timestamp(text)
    except (ValueError, TypeError):
        return None
    if pd.isna(ts):
        return None
    aware = cast(pd.Timestamp, ts)
    if aware.tz is None:
        aware = aware.tz_localize("UTC")
    else:
        aware = aware.tz_convert("UTC")
    return int(aware.timestamp() * 1000)


def slice_frame_for_chart(
    frame: pd.DataFrame,
    trades: list[dict[str, Any]],
    *,
    pad_bars: int = DEFAULT_PAD_BARS,
    max_bars: int = DEFAULT_MAX_BARS,
) -> pd.DataFrame:
    """Return a subset of OHLCV rows centered on the trade span when the series is long."""
    if frame.empty or len(frame) <= max_bars:
        return frame
    if not trades:
        return frame.iloc[-max_bars:]
    index = pd.DatetimeIndex(frame.index)
    t_start = pd.Timestamp(trades[0]["entry_time"])
    t_end = pd.Timestamp(trades[-1]["exit_time"])
    if t_start.tz is None:
        t_start = t_start.tz_localize("UTC")
    if t_end.tz is None:
        t_end = t_end.tz_localize("UTC")
    i0 = int(index.searchsorted(cast(Any, t_start), side="left"))
    i1 = int(index.searchsorted(cast(Any, t_end), side="right"))
    start = max(0, i0 - pad_bars)
    end = min(len(frame), i1 + pad_bars)
    if end - start > max_bars:
        mid = (start + end) // 2
        start = max(0, mid - max_bars // 2)
        end = min(len(frame), start + max_bars)
    return frame.iloc[start:end]


def ohlc_bars(frame: pd.DataFrame) -> list[OhlcBar]:
    bars: list[OhlcBar] = []
    opens = frame["open"]
    highs = frame["high"]
    lows = frame["low"]
    closes = frame["close"]
    for i in range(len(frame)):
        ms = timestamp_ms(frame.index[i])
        if ms is None:
            continue
        bars.append(
            OhlcBar(
                ms=ms,
                open=float(opens.iloc[i]),
                high=float(highs.iloc[i]),
                low=float(lows.iloc[i]),
                close=float(closes.iloc[i]),
            ),
        )
    return bars


def trade_markers(trades: list[dict[str, Any]]) -> tuple[list[TradeMarker], list[TradeMarker]]:
    entries: list[TradeMarker] = []
    exits: list[TradeMarker] = []
    for trade in trades:
        entry_ms = timestamp_ms(trade["entry_time"])
        if entry_ms is not None:
            entries.append(TradeMarker(entry_ms, float(trade["entry_price"])))
        exit_ms = timestamp_ms(trade["exit_time"])
        if exit_ms is not None:
            exits.append(TradeMarker(exit_ms, float(trade["exit_price"])))
    return entries, exits
