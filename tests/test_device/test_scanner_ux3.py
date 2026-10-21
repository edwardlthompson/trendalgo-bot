"""S-Scanner-UX3: Watch checkbox persist, coin health, column filter row."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from trendalgo.device.coin_health import compute_coin_health
from trendalgo.device.lts_scan_model import load_watchlist, normalize_coin, save_watchlist

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

from PySide6.QtWidgets import QCheckBox, QComboBox, QLabel  # noqa: E402
from pytestqt.qtbot import QtBot  # noqa: E402

from trendalgo.device import strings as S  # noqa: E402
from trendalgo.device.context import DeviceContext  # noqa: E402
from trendalgo.device.views.scanner_column_filter_row import FILTER_ROW, GainMinEdit  # noqa: E402
from trendalgo.device.views.scanner_page import ScannerPage  # noqa: E402
from trendalgo.device.views.scanner_table import COL_WATCH, fill_lts_table  # noqa: E402
from trendalgo.device.views.widgets import read_only_table  # noqa: E402


def test_health_differs_from_uniformity_when_gains_differ() -> None:
    low = normalize_coin(
        {
            "symbol": "A",
            "uniformity_score": 60.0,
            "gains": {"7d": -40.0},
            "volume_acceleration_pct": -40.0,
            "hv_7d_pct": 80.0,
            "max_drawdown_pct": -60.0,
        }
    )
    high = normalize_coin(
        {
            "symbol": "B",
            "uniformity_score": 60.0,
            "gains": {"7d": 40.0},
            "volume_acceleration_pct": 40.0,
            "hv_7d_pct": 10.0,
            "max_drawdown_pct": -5.0,
        }
    )
    assert low["uniformity_score"] == high["uniformity_score"]
    assert low["health_score"] != high["health_score"]
    assert high["health_score"] > low["health_score"]
    assert compute_coin_health(high) == high["health_score"]


def test_watch_checkbox_persists(tmp_path: Path, qtbot: QtBot) -> None:
    table = read_only_table(S.SCANNER_LTS_HEADERS, S.SCANNER_TITLE)
    qtbot.addWidget(table)
    seen: list[tuple[str, bool]] = []

    def on_watch(pair: str, checked: bool) -> None:
        seen.append((pair, checked))
        watch = load_watchlist(tmp_path)
        symbol = pair.split("/")[0]
        cleaned = [p for p in watch if p != pair and p != symbol]
        if checked:
            cleaned.append(pair)
        save_watchlist(tmp_path, cleaned)

    fill_lts_table(
        table,
        [{"symbol": "BTC", "pair": "BTC/USD", "listed_on": ["kraken"]}],
        watch=set(),
        on_watch=on_watch,
    )
    host = table.cellWidget(0, COL_WATCH)
    assert host is not None
    box = host.findChild(QCheckBox)
    assert box is not None
    assert not box.isChecked()
    box.setChecked(True)
    assert seen == [("kraken:BTC", True)]
    assert "kraken:BTC" in load_watchlist(tmp_path)

    seen.clear()
    box.setChecked(False)
    assert seen == [("kraken:BTC", False)]
    assert "kraken:BTC" not in load_watchlist(tmp_path)


def test_scanner_page_omits_title_subtitle(qtbot: QtBot, ctx: DeviceContext) -> None:
    page = ScannerPage(ctx)
    qtbot.addWidget(page)
    texts = {label.text() for label in page.findChildren(QLabel)}
    assert S.SCANNER_TITLE not in texts
    assert S.SCANNER_SUBTITLE not in texts
    assert page._table.accessibleName() == S.SCANNER_TITLE


def test_gain_spin_keeps_focus_widget_across_filter(qtbot: QtBot, ctx: DeviceContext) -> None:
    page = ScannerPage(ctx)
    qtbot.addWidget(page)
    page.show()
    page._coins = [
        {
            "symbol": "LOW",
            "pair": "LOW/USD",
            "listed_on": ["kraken"],
            "gains": {"7d": 3.0, "30d": 5.0},
            "uniformity_score": 50.0,
            "health_score": 55.0,
        },
        {
            "symbol": "HIGH",
            "pair": "HIGH/USD",
            "listed_on": ["kraken"],
            "gains": {"7d": 12.0, "30d": 20.0},
            "uniformity_score": 50.0,
            "health_score": 55.0,
        },
    ]
    page._show_tab()
    edit = page._col_filters.gain_7d
    edit.setValue(7)
    page._on_filter()
    assert [c["symbol"] for c in page._shown] == ["HIGH"]
    assert page._table.cellWidget(FILTER_ROW, 3).findChild(type(edit)) is edit
    assert edit.value() == 7


def test_strict_column_filter_keeps_filter_row_visible(qtbot: QtBot, ctx: DeviceContext) -> None:
    page = ScannerPage(ctx)
    qtbot.addWidget(page)
    page._coins = [
        {
            "symbol": "BTC",
            "pair": "BTC/USD",
            "listed_on": ["kraken"],
            "gains": {"7d": 2.0, "30d": 5.0},
            "uniformity_score": 50.0,
            "health_score": 55.0,
        }
    ]
    page.show()
    page._col_filters.gain_7d.setValue(7)
    page._show_tab()
    assert page._shown == []
    assert not page._table.isHidden()
    assert page._table.cellWidget(FILTER_ROW, 3) is not None
    assert page._col_filters.gain_7d.value() == 7
    assert S.SCANNER_FILTER_NONE_STATUS in page._status.text()
    page._col_filters.gain_7d.setValue(None)
    page._show_tab()
    assert len(page._shown) == 1
    assert page._table.rowCount() >= 2


def test_column_filters_live_in_table_row_zero(qtbot: QtBot, ctx: DeviceContext) -> None:
    page = ScannerPage(ctx)
    qtbot.addWidget(page)
    page._coins = [
        {
            "symbol": "BTC",
            "pair": "BTC/USD",
            "listed_on": ["kraken"],
            "gains": {"7d": 10.0, "30d": 20.0},
            "uniformity_score": 50.0,
            "health_score": 55.0,
        }
    ]
    page._show_tab()
    table = page._table
    assert table.rowCount() >= 2
    host = table.cellWidget(FILTER_ROW, 3)
    assert host is not None
    assert host.findChild(GainMinEdit) is page._col_filters.gain_7d
    spark_host = table.cellWidget(FILTER_ROW, 4)
    assert spark_host is not None
    assert spark_host.findChild(QComboBox) is page._col_filters.chart_dist_7d
    # Data row starts after the filter row.
    data_host = table.cellWidget(1, COL_WATCH)
    assert data_host is not None
    assert data_host.findChild(QCheckBox) is not None
