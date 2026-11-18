"""Oracle max must not show Create Bot (SS ceiling only)."""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QPushButton, QTableWidget

from trendalgo.device import strings as S
from trendalgo.device.backtest_results_ui import CREATE_BOT_COL
from trendalgo.device.views.scanner_results_fill import populate_results_table


def test_oracle_create_bot_is_dash(qtbot) -> None:
    table = QTableWidget()
    table.setColumnCount(len(S.BACKTEST_RESULT_HEADERS))
    qtbot.addWidget(table)
    status = QLabel()
    rows = [
        {"indicator": "RSI", "timeframe": "1h", "net_pct": 5.0, "trades": 3, "wins": 2},
        {"indicator": "Oracle max", "timeframe": "1h", "net_pct": 40.0, "trades": 1, "wins": 1},
        {"indicator": "B&H", "timeframe": "1h", "net_pct": 2.0, "trades": 0, "wins": 0},
    ]
    populate_results_table(
        table,
        rows,
        coin={"symbol": "BTC", "pair": "BTC/USD"},
        pair="BTC/USD",
        heatmap=False,
        status=status,
        parent=table,
        filter_row=None,
        on_create_bot=lambda _f, _n: "",
        indicator_label=lambda name, **_k: name,
    )
    # RSI → Create Bot button; Oracle + B&H → em dash label.
    rsi_host = table.cellWidget(0, CREATE_BOT_COL)
    oracle_host = table.cellWidget(1, CREATE_BOT_COL)
    bh_host = table.cellWidget(2, CREATE_BOT_COL)
    assert rsi_host is not None
    assert oracle_host is not None
    assert bh_host is not None
    assert rsi_host.findChildren(QPushButton)
    assert any(b.text() == S.SCANNER_CREATE_BOT for b in rsi_host.findChildren(QPushButton))
    assert not oracle_host.findChildren(QPushButton)
    assert not bh_host.findChildren(QPushButton)
    assert any(lab.text() == "—" for lab in oracle_host.findChildren(QLabel))
