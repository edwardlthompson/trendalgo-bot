"""Fixed 30-day lookback for All-TA scans."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pandas as pd
import pytest

from trendalgo.backtest.load_days import (
    SCAN_LOOKBACK_DAYS,
    SCAN_LOOKBACK_HOURS,
    days_for_timeframe,
    trim_closes,
    trim_ohlcv_frame,
)
from trendalgo.backtest.ta_simulator import simulate_buy_and_hold
from trendalgo.exchanges.fees import ExchangeFeeSchedule


def test_all_timeframes_use_30_days() -> None:
    assert SCAN_LOOKBACK_DAYS == 30
    for tf in ("1h", "4h", "12h", "24h", "1d"):
        assert days_for_timeframe(tf) == 30


def test_trim_ohlcv_frame_keeps_last_30_calendar_days() -> None:
    end = datetime(2026, 3, 31, 12, tzinfo=UTC)
    idx = pd.date_range(end - timedelta(days=59), end, freq="1h", tz="UTC")
    frame = pd.DataFrame(
        {
            "open": range(len(idx)),
            "high": range(len(idx)),
            "low": range(len(idx)),
            "close": [100.0 + i * 0.01 for i in range(len(idx))],
            "volume": 1.0,
        },
        index=idx,
    )
    trimmed = trim_ohlcv_frame(frame, days=30)
    span = (trimmed.index.max() - trimmed.index.min()).total_seconds() / 86_400
    assert span <= 30.0 + 1.0 / 24
    assert trimmed.index.max() == frame.index.max()
    assert len(trimmed) < len(frame)


def test_trim_closes_keeps_last_n_hours() -> None:
    closes = [float(i) for i in range(1000)]
    out = trim_closes(closes, hours=SCAN_LOOKBACK_HOURS)
    assert len(out) == SCAN_LOOKBACK_HOURS
    assert out[0] == closes[-SCAN_LOOKBACK_HOURS]
    assert out[-1] == closes[-1]


def test_bh_on_trimmed_matches_last_30d_price_move() -> None:
    end = datetime(2026, 3, 31, tzinfo=UTC)
    idx = pd.date_range(end - timedelta(days=59), end, freq="1h", tz="UTC")
    closes = [50.0 + i * 0.02 for i in range(len(idx))]
    frame = pd.DataFrame(
        {"open": closes, "high": closes, "low": closes, "close": closes, "volume": 1.0},
        index=idx,
    )
    trimmed = trim_ohlcv_frame(frame, days=30)
    fee = ExchangeFeeSchedule(
        exchange_id="test",
        tier="zero",
        maker_pct=0.0,
        taker_pct=0.0,
        source_url="https://example.test",
    )
    bh = simulate_buy_and_hold(trimmed, stake_usd=1000.0, fee=fee)
    assert bh is not None
    first, last = float(trimmed["close"].iloc[0]), float(trimmed["close"].iloc[-1])
    expect = ((last / first) - 1.0) * 1000.0
    assert bh["net_profit"] == pytest.approx(expect, rel=1e-6)
