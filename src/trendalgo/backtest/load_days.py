"""Fixed lookback for All-TA / pair scans — always 30 days (apples-to-apples)."""

from __future__ import annotations

import pandas as pd

# Every strategy × TF comparison uses the same calendar window.
SCAN_LOOKBACK_DAYS = 30
SCAN_LOOKBACK_HOURS = SCAN_LOOKBACK_DAYS * 24


def days_for_timeframe(_timeframe: str = "", *, min_bars: int | None = None) -> int:
    """Return the fixed scan lookback (ignores TF — slow TFs may simply lack bars)."""
    del min_bars  # kept for call-site compatibility
    return SCAN_LOOKBACK_DAYS


def trim_ohlcv_frame(frame: pd.DataFrame, days: int = SCAN_LOOKBACK_DAYS) -> pd.DataFrame:
    """Keep bars in the last ``days`` calendar window ending at the newest timestamp."""
    if frame is None or frame.empty or days <= 0:
        return frame
    raw_idx = frame.index
    if not isinstance(raw_idx, pd.DatetimeIndex):
        return frame
    frame = frame.copy()
    aware: pd.DatetimeIndex
    if raw_idx.tz is None:
        aware = raw_idx.tz_localize("UTC")
    else:
        aware = raw_idx.tz_convert("UTC")
    frame.index = aware
    end = aware[-1]
    start = end - pd.Timedelta(days=int(days))
    trimmed = frame.loc[aware >= start]
    return trimmed if not trimmed.empty else frame.iloc[-1:].copy()


def trim_closes(closes: list[float], *, hours: int = SCAN_LOOKBACK_HOURS) -> list[float]:
    """Keep the last ``hours`` closes when timestamps are unavailable (1h series)."""
    if hours <= 0 or len(closes) <= hours:
        return list(closes)
    return list(closes[-hours:])
