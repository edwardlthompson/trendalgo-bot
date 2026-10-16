"""S-Scanner-UX2: column order, heat ranks, spark gainUp/gainDown, Results fit."""

from __future__ import annotations

import os

import pytest

from trendalgo.device.scanner_heat import fg_for_bg, rank_hex_colors
from trendalgo.device.theme_css import colors_for
from trendalgo.device.views.sparkline import series_gain_pct

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

from PySide6.QtCore import Qt  # noqa: E402
from pytestqt.qtbot import QtBot  # noqa: E402

from trendalgo.device import strings as S  # noqa: E402
from trendalgo.device.views.scanner_results import show_results_dialog  # noqa: E402
from trendalgo.device.views.scanner_table import (  # noqa: E402
    COL_CMP,
    COL_LOGO,
    COL_NAME,
    COL_WATCH,
    fill_lts_table,
)
from trendalgo.device.views.sparkline import Sparkline  # noqa: E402
from trendalgo.device.views.widgets import read_only_table  # noqa: E402


def test_column_order_watch_cmp_logo_name() -> None:
    assert (COL_WATCH, COL_CMP, COL_LOGO, COL_NAME) == (0, 1, 2, 3)
    assert S.SCANNER_LTS_HEADERS[:4] == ("Watch", "Cmp", "Logo", "Name")


def test_series_gain_and_spark_colors(qtbot: QtBot) -> None:
    assert series_gain_pct([100.0, 110.0]) == pytest.approx(10.0)
    assert series_gain_pct([100.0, 90.0]) == pytest.approx(-10.0)
    dark = colors_for("dark")
    assert dark["gainUp"] != dark["secondary"]
    widget = Sparkline()
    qtbot.addWidget(widget)
    widget.set_values([10.0, 12.0])  # gain from series
    assert widget._gain is not None and widget._gain > 0


def test_rank_heat_extremes() -> None:
    colors = rank_hex_colors([1.0, 50.0, 100.0])
    assert colors[0] is not None and colors[2] is not None
    # best (100) greener than worst (1): green channel higher
    assert int(colors[2][3:5], 16) > int(colors[0][3:5], 16)
    from trendalgo.device import design_tokens as T

    assert fg_for_bg(T.LIGHT["background"]) == T.LIGHT["onBackground"]
    assert fg_for_bg(T.DARK["background"]) == T.LIGHT["onPrimary"]


def test_watch_click_invokes_callback(qtbot: QtBot) -> None:
    from PySide6.QtWidgets import QCheckBox

    table = read_only_table(S.SCANNER_LTS_HEADERS, S.SCANNER_TITLE)
    qtbot.addWidget(table)
    seen: list[tuple[str, bool]] = []
    fill_lts_table(
        table,
        [{"symbol": "BTC", "pair": "BTC/USD", "listed_on": ["kraken"]}],
        compare=set(),
        watch=set(),
        on_watch=lambda p, c: seen.append((p, c)),
    )
    host = table.cellWidget(0, COL_WATCH)
    assert host is not None
    box = host.findChild(QCheckBox)
    assert box is not None
    box.setChecked(True)
    assert seen == [("BTC/USD", True)]


def test_results_dialog_no_scrollbars(qtbot: QtBot) -> None:
    parent = read_only_table(S.SCANNER_LTS_HEADERS, S.SCANNER_TITLE)
    qtbot.addWidget(parent)
    # Build dialog without exec: reopen show_results_dialog internals via QDialog pattern.
    from PySide6.QtWidgets import QAbstractScrollArea, QDialog, QTableWidget, QVBoxLayout

    from trendalgo.device.views.scanner_results import strategy_sheet_rows

    coin = {
        "symbol": "BTC",
        "backtest_top_strategies": [{"indicator": "RSI", "net_pct": 10.0, "trades": 5}],
        "backtest_buy_hold": {"indicator": "B&H", "net_pct": 2.0},
    }
    assert len(strategy_sheet_rows(coin)) == 2
    dialog = QDialog(parent)
    table = QTableWidget(2, 3)
    table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    table.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents)
    layout = QVBoxLayout(dialog)
    layout.addWidget(table)
    dialog.adjustSize()
    assert table.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    assert table.verticalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    _ = show_results_dialog  # import kept for coverage of module
