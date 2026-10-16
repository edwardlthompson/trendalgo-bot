"""Qt smoke for Backtest page columns, heatmap toggle, asterisks."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

from pytestqt.qtbot import QtBot  # noqa: E402

from trendalgo.device import strings as S  # noqa: E402
from trendalgo.device.context import DeviceContext  # noqa: E402
from trendalgo.device.views.backtest_page import BacktestPage  # noqa: E402
from trendalgo.device.workers import WorkerPool  # noqa: E402


def test_backtest_columns_heatmap_and_asterisk(
    qtbot: QtBot, ctx: DeviceContext, pool: WorkerPool
) -> None:
    page = BacktestPage(ctx, pool)
    qtbot.addWidget(page)
    headers = [page._table.horizontalHeaderItem(i).text() for i in range(page._table.columnCount())]
    assert headers == list(S.BACKTEST_RESULT_HEADERS)
    assert page._heatmap.text() == S.SCANNER_COLOR_RANKS
    assert not page._heatmap.isChecked()
    page._rows = [
        {
            "indicator": "RSI",
            "timeframe": "1h",
            "params": {"timeperiod": 14, "entry_level": 30, "exit_level": 70},
            "net_pct": 10.0,
            "trades": 4,
            "win_pct": 50.0,
            "trailing_stop_pct": 2.0,
            "tsl_hits": 1,
        },
        {
            "indicator": "B&H",
            "timeframe": "1h",
            "params": {},
            "net_pct": 3.0,
            "trades": "-",
            "win_pct": "-",
            "trailing_stop_pct": None,
            "tsl_hits": 0,
        },
    ]
    page._all_rows = list(page._rows)
    page._pair.setText("BTC/USD")
    page._fill_table()
    # Row 0 is the filter strip; strategy rows start at 1.
    assert page._table.item(1, 0).text().endswith(" *")
    assert "buy & hold" in page._table.item(2, 0).text()
    page._heatmap.setChecked(True)
    page._fill_table()
    assert page._table.rowCount() == 3
