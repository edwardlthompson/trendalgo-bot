"""Resample OHLCV frames from a fine base (1m or 1h) to coarser TFs."""

from __future__ import annotations

import re
from collections.abc import Iterable

import pandas as pd

from trendalgo.backtest.heartbeat_tf import timeframe_minutes
from trendalgo.ta.frame_prep import stamp_scan_frame

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


def resample_ohlcv(
    frame: pd.DataFrame,
    timeframe: str,
    *,
    base_timeframe: str | None = None,
) -> pd.DataFrame:
    """Resample base OHLCV to ``timeframe`` (1m/5m/…/Nh/1d)."""
    text = str(timeframe).strip().lower()
    base_mins = timeframe_minutes(base_timeframe) if base_timeframe else _infer_base_minutes(frame)
    target_mins = timeframe_minutes(text)
    if target_mins is not None and base_mins is not None and target_mins == base_mins:
        return stamp_scan_frame(frame)
    if text in ("1h",) and base_mins == 60:
        return stamp_scan_frame(frame)

    rule = _pandas_rule(text)
    if rule is None:
        raise ValueError(f"Unsupported timeframe: {timeframe}")
    if target_mins is not None and base_mins is not None and target_mins < base_mins:
        raise ValueError(f"Cannot resample {base_mins}m bars down to {timeframe}")

    resampled = frame.resample(rule).agg(_AGG)
    return stamp_scan_frame(pd.DataFrame(resampled).dropna(how="any"))


def frames_from_1h(frame_1h: pd.DataFrame, timeframes: Iterable[str]) -> dict[str, pd.DataFrame]:
    """Build Nh frames from one 1h frame (no network I/O)."""
    return frames_from_base(frame_1h, timeframes, base_timeframe="1h")


def frames_from_base(
    frame: pd.DataFrame,
    timeframes: Iterable[str],
    *,
    base_timeframe: str | None = None,
) -> dict[str, pd.DataFrame]:
    """Build TF frames from one fine base frame (1m or 1h)."""
    out: dict[str, pd.DataFrame] = {}
    for tf in timeframes:
        key = str(tf).strip()
        if not key:
            continue
        try:
            out[key] = resample_ohlcv(frame, key, base_timeframe=base_timeframe)
        except ValueError:
            continue
    return out


def _infer_base_minutes(frame: pd.DataFrame) -> int | None:
    if frame is None or len(frame) < 2:
        return None
    idx = frame.index
    if not isinstance(idx, pd.DatetimeIndex):
        return None
    diffs = idx.asi8[1:] - idx.asi8[:-1]
    pos = diffs[diffs > 0]
    if len(pos) == 0:
        return None
    # Minimum positive step avoids overnight/weekend/holiday market-hour gaps.
    return max(1, int(round(float(pos.min()) / 60_000_000_000.0)))
