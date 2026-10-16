"""Qt smoke for the backtest candlestick chart."""

from __future__ import annotations

import pandas as pd
from pytestqt.qtbot import QtBot

from trendalgo.device import strings as S
from trendalgo.device.jobs import synthetic_frame
from trendalgo.device.views.candle_chart import CandleChart


def test_empty_chart_shows_hint(qtbot: QtBot) -> None:
    chart = CandleChart()
    qtbot.addWidget(chart)
    assert not chart._empty.isHidden()
    assert chart._empty.text() == S.BACKTEST_CHART_EMPTY


def test_chart_draws_candles_and_markers(qtbot: QtBot) -> None:
    index = pd.date_range("2024-01-01", periods=120, freq="h", tz="UTC")
    frame = synthetic_frame(120).set_index(index)
    trades = [
        {
            "entry_time": str(index[40]),
            "exit_time": str(index[55]),
            "entry_price": float(frame.iloc[40]["close"]),
            "exit_price": float(frame.iloc[55]["close"]),
            "pnl_pct": 1.0,
            "exit_reason": "signal",
        },
    ]
    chart = CandleChart()
    qtbot.addWidget(chart)
    chart.set_data(frame, trades)
    assert chart._empty.isHidden()
    assert not chart._view.isHidden()
    assert chart._candles.count() > 0
    assert chart._entries.count() == 1
    assert chart._exits.count() == 1
