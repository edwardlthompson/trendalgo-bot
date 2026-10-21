"""Dense LTS scanner table widgets (PWA look)."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

from PySide6.QtWidgets import QCheckBox, QPushButton, QTableWidget  # noqa: E402
from pytestqt.qtbot import QtBot  # noqa: E402

from trendalgo.device import strings as S  # noqa: E402
from trendalgo.device.views.scanner_table import (  # noqa: E402
    COL_RESULTS,
    COL_SPARK7,
    COL_WATCH,
    COLUMNS,
    fill_lts_table,
)
from trendalgo.device.views.sparkline import Sparkline  # noqa: E402
from trendalgo.device.views.widgets import read_only_table  # noqa: E402


def test_fill_lts_table_wires_watch_and_disabled_results(qtbot: QtBot) -> None:
    table = read_only_table(S.SCANNER_LTS_HEADERS, S.SCANNER_TITLE)
    qtbot.addWidget(table)
    toggled: list[tuple[str, bool]] = []
    fill_lts_table(
        table,
        [
            {
                "symbol": "BTC",
                "pair": "BTC/USD",
                "name": "BTC",
                "gains": {"7d": 40.0, "30d": 50.0},
                "closes_1h": [1.0, 1.1, 1.2],
                "listed_on": ["kraken"],
                "is_new": True,
            }
        ],
        on_watch=lambda pair, checked: toggled.append((pair, checked)),
    )
    assert table.columnCount() == COLUMNS
    assert table.rowCount() == 1
    assert "Cmp" not in S.SCANNER_LTS_HEADERS
    watch_host = table.cellWidget(0, COL_WATCH)
    assert watch_host is not None
    box = watch_host.findChild(QCheckBox)
    assert box is not None
    box.setChecked(True)
    assert toggled == [("kraken:BTC", True)]
    results = table.cellWidget(0, COL_RESULTS)
    assert isinstance(results, QPushButton)
    assert not results.isEnabled()
    spark_host = table.cellWidget(0, COL_SPARK7)
    assert spark_host is not None
    spark = spark_host.findChild(Sparkline)
    assert isinstance(spark, Sparkline)


def test_results_enabled_when_bot_best_present(qtbot: QtBot) -> None:
    table = QTableWidget()
    qtbot.addWidget(table)
    opened: list[str] = []
    fill_lts_table(
        table,
        [
            {
                "symbol": "ETH",
                "pair": "ETH/USD",
                "bot_best_net_pct": 120.0,
                "bot_best_label": "16% TSL",
                "listed_on": ["kraken"],
            }
        ],
        on_results=lambda coin: opened.append(str(coin["symbol"])),
    )
    btn = table.cellWidget(0, COL_RESULTS)
    assert isinstance(btn, QPushButton)
    assert btn.isEnabled()
    btn.click()
    assert opened == ["ETH"]
