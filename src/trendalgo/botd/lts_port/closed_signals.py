"""Closed-bar signals for the streaming port: the indicator on the last lookback_bars rows (L5, L8)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd

from trendalgo.lts_vendor.backtesting.signals import generate_indicator_signals

MIN_LOOKBACK_BARS = 500  # L5: EWM-based indicators have negligible decay after 500 closed bars


def last_closed_signals(
    indicator: str,
    frame: pd.DataFrame,
    params: Mapping[str, Any],
    *,
    lookback_bars: int,
) -> tuple[bool, bool]:
    """Buy and sell flags for the newest row. Pass closed bars only (see drop_forming_bar)."""
    if lookback_bars < MIN_LOOKBACK_BARS:
        raise ValueError(f"lookback_bars must be at least {MIN_LOOKBACK_BARS}")
    window = frame.tail(lookback_bars)
    if window.empty:
        raise ValueError("no closed bars to signal on")
    buy, sell = generate_indicator_signals(indicator, window, dict(params))
    buy_flags = buy.reindex(window.index).fillna(False).astype(bool)
    sell_flags = sell.reindex(window.index).fillna(False).astype(bool)
    return bool(buy_flags.iloc[-1]), bool(sell_flags.iloc[-1])


def drop_forming_bar(
    frame: pd.DataFrame, *, interval: pd.Timedelta, now: pd.Timestamp
) -> pd.DataFrame:
    """Keep only rows that have closed by `now`. A row opens at its index and closes after interval (L8)."""
    return frame.loc[frame.index + interval <= now]
