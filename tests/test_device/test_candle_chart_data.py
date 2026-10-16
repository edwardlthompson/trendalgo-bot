"""Pure logic for backtest candle chart windowing and markers."""

from __future__ import annotations

import pandas as pd

from trendalgo.device.candle_chart_data import (
    ohlc_bars,
    slice_frame_for_chart,
    timestamp_ms,
    trade_markers,
)
from trendalgo.device.jobs import synthetic_frame


def test_timestamp_ms_parses_iso_and_utc_index() -> None:
    assert timestamp_ms("2024-01-02T12:00:00+00:00") == 1_704_196_800_000
    index = pd.date_range("2024-01-01", periods=3, freq="h", tz="UTC")
    frame = synthetic_frame(3).set_index(index)
    bars = ohlc_bars(frame)
    assert len(bars) == 3
    assert bars[0].ms < bars[-1].ms


def test_slice_frame_centers_on_trades_when_history_is_long() -> None:
    index = pd.date_range("2024-01-01", periods=400, freq="h", tz="UTC")
    frame = synthetic_frame(400).set_index(index)
    trades = [
        {
            "entry_time": str(index[200]),
            "exit_time": str(index[210]),
            "entry_price": 100.0,
            "exit_price": 101.0,
        },
    ]
    window = slice_frame_for_chart(frame, trades, pad_bars=5, max_bars=50)
    assert len(window) <= 50
    assert window.index[0] <= index[195]
    assert window.index[-1] >= index[215]
    assert len(window) >= 11


def test_trade_markers_use_entry_and_exit_prices() -> None:
    trades = [
        {
            "entry_time": "2024-01-02T00:00:00+00:00",
            "exit_time": "2024-01-03T00:00:00+00:00",
            "entry_price": 99.5,
            "exit_price": 102.25,
        },
    ]
    entries, exits = trade_markers(trades)
    assert len(entries) == 1 and len(exits) == 1
    assert entries[0].price == 99.5
    assert exits[0].price == 102.25
