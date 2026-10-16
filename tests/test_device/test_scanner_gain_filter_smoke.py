"""Smoke: type into 7D/30D gain filters and confirm rows actually filter."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from pytestqt.qtbot import QtBot  # noqa: E402

from trendalgo.device.context import DeviceContext  # noqa: E402
from trendalgo.device.views.scanner_column_filter_row import GainMinEdit  # noqa: E402
from trendalgo.device.views.scanner_page import ScannerPage  # noqa: E402


def _coins() -> list[dict]:
    return [
        {
            "symbol": "LOW",
            "pair": "LOW/USD",
            "listed_on": ["kraken"],
            "gains": {"7d": 3.0, "30d": 4.0},
            "uniformity_score": 50.0,
            "health_score": 55.0,
        },
        {
            "symbol": "MID",
            "pair": "MID/USD",
            "listed_on": ["kraken"],
            "gains": {"7d": 8.0, "30d": 9.0},
            "uniformity_score": 50.0,
            "health_score": 55.0,
        },
        {
            "symbol": "HIGH",
            "pair": "HIGH/USD",
            "listed_on": ["kraken"],
            "gains": {"7d": 20.0, "30d": 40.0},
            "uniformity_score": 50.0,
            "health_score": 55.0,
        },
    ]


def test_type_7d_min_filters_rows(qtbot: QtBot, ctx: DeviceContext) -> None:
    page = ScannerPage(ctx)
    qtbot.addWidget(page)
    page.show()
    page._coins = _coins()
    page._show_tab()
    qtbot.waitExposed(page)

    edit = page._col_filters.gain_7d
    assert isinstance(edit, GainMinEdit)
    edit.setFocus()
    QTest.keyClicks(edit, "7")
    QTest.keyClick(edit, Qt.Key.Key_Return)
    assert edit.value() == 7
    assert [c["symbol"] for c in page._shown] == ["MID", "HIGH"]


def test_type_30d_min_filters_rows(qtbot: QtBot, ctx: DeviceContext) -> None:
    page = ScannerPage(ctx)
    qtbot.addWidget(page)
    page.show()
    page._coins = _coins()
    page._show_tab()
    qtbot.waitExposed(page)

    edit = page._col_filters.gain_30d
    edit.setFocus()
    QTest.keyClicks(edit, "10")
    QTest.keyClick(edit, Qt.Key.Key_Return)
    assert edit.value() == 10
    assert [c["symbol"] for c in page._shown] == ["HIGH"]


def test_best_bt_and_bot_vs_bh_filters(qtbot: QtBot, ctx: DeviceContext) -> None:
    page = ScannerPage(ctx)
    qtbot.addWidget(page)
    page.show()
    page._coins = [
        {
            "symbol": "BOT",
            "pair": "BOT/USD",
            "listed_on": ["kraken"],
            "gains": {"7d": 10.0, "30d": 10.0},
            "bot_best_net_pct": 80.0,
            "bot_vs_bh_pct": 15.0,
        },
        {
            "symbol": "HOLD",
            "pair": "HOLD/USD",
            "listed_on": ["kraken"],
            "gains": {"7d": 10.0, "30d": 10.0},
            "bot_best_net_pct": 20.0,
            "bot_vs_bh_pct": -10.0,
        },
    ]
    page._show_tab()
    page._col_filters.best_bt.setFocus()
    QTest.keyClicks(page._col_filters.best_bt, "50")
    QTest.keyClick(page._col_filters.best_bt, Qt.Key.Key_Return)
    assert [c["symbol"] for c in page._shown] == ["BOT"]
    page._col_filters.best_bt.setValue(0)
    page._col_filters.bot_vs_bh.setCurrentIndex(page._col_filters.bot_vs_bh.findData("neg"))
    page._on_filter()
    assert [c["symbol"] for c in page._shown] == ["HOLD"]


def test_type_over_empty_without_select_all(qtbot: QtBot, ctx: DeviceContext) -> None:
    """Regression: empty min% field must accept typed digits with no selectAll."""
    page = ScannerPage(ctx)
    qtbot.addWidget(page)
    page.show()
    page._coins = _coins()
    page._show_tab()
    edit = page._col_filters.gain_7d
    assert edit.value() == 0
    assert edit.text() == ""
    edit.setFocus()
    QTest.keyClicks(edit, "15")
    QTest.keyClick(edit, Qt.Key.Key_Return)
    assert edit.value() == 15
    assert [c["symbol"] for c in page._shown] == ["HIGH"]
