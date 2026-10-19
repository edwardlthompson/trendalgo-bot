"""Show Chart column helpers on Results / Backtest tables."""

from __future__ import annotations

from typing import Any

import pytest
from PySide6.QtWidgets import QDialog, QPushButton, QTableWidget
from pytestqt.qtbot import QtBot

from trendalgo.device import strings as S
from trendalgo.device.backtest_results_ui import CREATE_BOT_COL, SHOW_CHART_COL
from trendalgo.device.views.scanner_results import _show_chart_cell


def test_header_indices_match_show_chart_column() -> None:
    assert S.BACKTEST_RESULT_HEADERS[SHOW_CHART_COL] == "Show Chart"
    assert S.BACKTEST_RESULT_HEADERS[CREATE_BOT_COL] == "Create Bot"


def test_show_chart_cell_wires_button(qtbot: QtBot, monkeypatch: pytest.MonkeyPatch) -> None:
    table = QTableWidget(1, len(S.BACKTEST_RESULT_HEADERS))
    qtbot.addWidget(table)
    opened: list[dict[str, Any]] = []

    def _fake_dialog(
        parent: object,
        coin: dict[str, Any],
        **kwargs: Any,
    ) -> None:
        opened.append({"coin": coin, **kwargs})

    monkeypatch.setattr(
        "trendalgo.device.views.scanner_chart_dialog.show_scanner_chart_dialog",
        _fake_dialog,
    )
    monkeypatch.setattr(QDialog, "exec", lambda self: 0)

    row = {"indicator": "RSI", "timeframe": "1h", "net_pct": 12.0, "trades": 3}
    coin = {"symbol": "ETH", "pair": "ETH/USD"}
    _show_chart_cell(table, 0, row, coin=coin, parent=table)
    host = table.cellWidget(0, SHOW_CHART_COL)
    assert host is not None
    buttons = host.findChildren(QPushButton)
    assert buttons
    buttons[0].click()
    assert opened
    assert opened[0]["strategy_row"]["indicator"] == "RSI"
    assert opened[0]["price_only"] is False
