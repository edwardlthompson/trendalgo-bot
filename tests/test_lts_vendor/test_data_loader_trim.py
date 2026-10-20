"""BacktestDataLoader lookback trim (via shared helper used at load boundaries)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pandas as pd

from trendalgo.backtest.load_days import SCAN_LOOKBACK_DAYS, trim_ohlcv_frame


def test_trim_lookback_caps_60d_cache_to_30d() -> None:
    end = datetime(2026, 4, 1, tzinfo=UTC)
    idx = pd.date_range(end - timedelta(days=59), end, freq="1h", tz="UTC")
    frame = pd.DataFrame(
        {
            "open": 1.0,
            "high": 1.0,
            "low": 1.0,
            "close": 1.0,
            "volume": 1.0,
        },
        index=idx,
    )
    out = trim_ohlcv_frame(frame, SCAN_LOOKBACK_DAYS)
    span_h = (out.index.max() - out.index.min()).total_seconds() / 3600.0
    assert span_h <= SCAN_LOOKBACK_DAYS * 24 + 1
    assert len(out) < len(frame)
