"""Resample 1h OHLCV into Nh bars for heartbeat TFs."""

from __future__ import annotations

import pandas as pd

from trendalgo.backtest.ohlcv_resample import frames_from_1h, frames_from_base, resample_ohlcv


def _hourly(n: int = 48) -> pd.DataFrame:
    idx = pd.date_range("2024-01-01", periods=n, freq="h", tz="UTC")
    close = pd.Series(range(100, 100 + n), index=idx, dtype=float)
    return pd.DataFrame(
        {
            "open": close,
            "high": close + 1,
            "low": close - 1,
            "close": close,
            "volume": 1.0,
        },
        index=idx,
    )


def test_resample_3h_and_24h() -> None:
    frame = _hourly(48)
    three = resample_ohlcv(frame, "3h")
    assert len(three) == 16
    day = resample_ohlcv(frame, "24h")
    assert len(day) == 2
    same = resample_ohlcv(frame, "1h")
    assert len(same) == 48


def test_frames_from_1h_builds_grid() -> None:
    frame = _hourly(48)
    grid = frames_from_1h(frame, ("1h", "2h", "4h"))
    assert set(grid) == {"1h", "2h", "4h"}
    assert len(grid["1h"]) == 48
    assert len(grid["2h"]) == 24
    assert len(grid["4h"]) == 12


def test_gapped_equity_1h_frames_from_base() -> None:
    # Leading 48h weekend gap (idx[1]-idx[0] == 2880m) followed by 1h bars.
    t0 = pd.Timestamp("2024-01-05 20:00:00", tz="UTC")
    rest = pd.date_range("2024-01-07 20:00:00", periods=47, freq="h", tz="UTC")
    idx = pd.DatetimeIndex([t0, *rest])
    close = pd.Series(range(100, 100 + len(idx)), index=idx, dtype=float)
    frame = pd.DataFrame(
        {
            "open": close,
            "high": close + 1,
            "low": close - 1,
            "close": close,
            "volume": 100.0,
        },
        index=idx,
    )
    grid = frames_from_base(frame, ("1h", "2h", "4h", "24h"), base_timeframe="1h")
    assert set(grid) == {"1h", "2h", "4h", "24h"}
    assert len(grid["1h"]) == 48

    # Ultra-illiquid ticker with no adjacent 1h bars at all (3h gaps everywhere).
    thin_idx = pd.date_range("2024-01-08 00:00:00", periods=20, freq="3h", tz="UTC")
    thin_close = pd.Series(range(50, 50 + len(thin_idx)), index=thin_idx, dtype=float)
    thin = pd.DataFrame(
        {
            "open": thin_close,
            "high": thin_close + 1,
            "low": thin_close - 1,
            "close": thin_close,
            "volume": 10.0,
        },
        index=thin_idx,
    )
    thin_grid = frames_from_base(thin, ("1h", "4h", "24h"), base_timeframe="1h")
    assert "1h" in thin_grid
    assert len(thin_grid["1h"]) == 20
