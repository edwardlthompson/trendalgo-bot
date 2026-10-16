"""Resample 1h OHLCV into Nh bars for heartbeat TFs."""

from __future__ import annotations

import pandas as pd

from trendalgo.backtest.ohlcv_resample import frames_from_1h, resample_ohlcv


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
