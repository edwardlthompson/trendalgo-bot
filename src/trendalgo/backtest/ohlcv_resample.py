"""Resample 1h OHLCV frames to Nh / 1d bars."""

from __future__ import annotations

import re
from collections.abc import Iterable

import pandas as pd


def resample_ohlcv(frame_1h: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    """Resample hourly OHLCV to ``Nh`` (1–24) or daily."""
    if timeframe == "1h":
        return frame_1h

    if timeframe in ("1d", "daily"):
        rule = "1d"
    else:
        match = re.fullmatch(r"(\d+)h", str(timeframe).strip().lower())
        if not match:
            raise ValueError(f"Unsupported timeframe: {timeframe}")
        hours = int(match.group(1))
        if hours < 1 or hours > 24:
            raise ValueError(f"Unsupported timeframe: {timeframe}")
        if hours == 1:
            return frame_1h
        rule = f"{hours}h"

    resampled = frame_1h.resample(rule).agg(
        {
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum",
        }
    )
    out = pd.DataFrame(resampled).dropna(how="any")
    return out


def frames_from_1h(frame_1h: pd.DataFrame, timeframes: Iterable[str]) -> dict[str, pd.DataFrame]:
    """Build Nh frames from one 1h frame (no network I/O)."""
    out: dict[str, pd.DataFrame] = {}
    for tf in timeframes:
        key = str(tf).strip()
        if not key:
            continue
        out[key] = resample_ohlcv(frame_1h, key)
    return out
