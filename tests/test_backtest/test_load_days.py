"""Fixed 30-day lookback for All-TA scans."""

from __future__ import annotations

from trendalgo.backtest.load_days import SCAN_LOOKBACK_DAYS, days_for_timeframe


def test_all_timeframes_use_30_days() -> None:
    assert SCAN_LOOKBACK_DAYS == 30
    for tf in ("1h", "4h", "12h", "24h", "1d"):
        assert days_for_timeframe(tf) == 30
