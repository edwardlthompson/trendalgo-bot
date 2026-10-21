"""Resample OHLCV frames from a fine base (1m or 1h) to coarser TFs."""

from __future__ import annotations

import re
from collections.abc import Iterable

import pandas as pd

from trendalgo.backtest.heartbeat_tf import timeframe_minutes

_AGG = {
    "open": "first",
    "high": "max",
    "low": "min",
    "close": "last",
    "volume": "sum",
}


def _pandas_rule(timeframe: str) -> str | None:
    text = str(timeframe).strip().lower()
    if text in ("1d", "daily"):
        return "1d"
    m = re.fullmatch(r"(\d+)m", text)
    if m:
        return f"{int(m.group(1))}min"
    m = re.fullmatch(r"(\d+)h", text)
    if m:
        hours = int(m.group(1))
        if 1 <= hours <= 24:
            return f"{hours}h"
    return None


def resample_ohlcv(frame: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    """Resample base OHLCV to ``timeframe`` (1m/5m/…/Nh/1d)."""
    text = str(timeframe).strip().lower()
    base_mins = _infer_base_minutes(frame)
    target_mins = timeframe_minutes(text)
    if target_mins is not None and base_mins is not None and target_mins == base_mins:
        return frame
    if text in ("1h",) and base_mins == 60:
        return frame

    rule = _pandas_rule(text)
    if rule is None:
        raise ValueError(f"Unsupported timeframe: {timeframe}")
    if target_mins is not None and base_mins is not None and target_mins < base_mins:
        raise ValueError(f"Cannot resample {base_mins}m bars down to {timeframe}")

    resampled = frame.resample(rule).agg(_AGG)
    return pd.DataFrame(resampled).dropna(how="any")


def frames_from_1h(frame_1h: pd.DataFrame, timeframes: Iterable[str]) -> dict[str, pd.DataFrame]:
    """Build Nh frames from one 1h frame (no network I/O)."""
    return frames_from_base(frame_1h, timeframes)


def frames_from_base(frame: pd.DataFrame, timeframes: Iterable[str]) -> dict[str, pd.DataFrame]:
    """Build TF frames from one fine base frame (1m or 1h)."""
    out: dict[str, pd.DataFrame] = {}
    for tf in timeframes:
        key = str(tf).strip()
        if not key:
            continue
        out[key] = resample_ohlcv(frame, key)
    return out


def _infer_base_minutes(frame: pd.DataFrame) -> int | None:
    if frame is None or len(frame) < 2:
        return None
    idx = frame.index
    if not isinstance(idx, pd.DatetimeIndex):
        return None
    delta = (idx[1] - idx[0]).total_seconds()
    if delta <= 0:
        return None
    return max(1, int(round(delta / 60.0)))
