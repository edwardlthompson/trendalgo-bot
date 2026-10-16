"""Scanner UX polish: listing URLs, hourly dist match, Results sheet, Watch column."""

from __future__ import annotations

import os

import pytest

from trendalgo.device.coin_listing import coin_listing_url
from trendalgo.device.lts_scan_model import closes_pct_from_high, normalize_coin
from trendalgo.device.views.scanner_results import strategy_sheet_rows

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

from PySide6.QtWidgets import QCheckBox  # noqa: E402
from pytestqt.qtbot import QtBot  # noqa: E402

from trendalgo.device import strings as S  # noqa: E402
from trendalgo.device.views.scanner_table import (  # noqa: E402
    COL_WATCH,
    COLUMNS,
    fill_lts_table,
)
from trendalgo.device.views.widgets import read_only_table  # noqa: E402


def test_coin_listing_url_precedence() -> None:
    assert "currencies/bitcoin" in coin_listing_url({"cmc_slug": "bitcoin", "symbol": "BTC"})
    assert "coingecko.com/en/coins/eth" in coin_listing_url({"slug": "eth", "symbol": "ETH"})
    assert "search/?q=XYZ" in coin_listing_url({"symbol": "XYZ"})


def test_hourly_7d_30d_dist_match_when_high_in_last_week() -> None:
    # 720 hours: older quiet period, then a spike high inside the last 168 bars.
    closes = [10.0] * 552 + [20.0] + [15.0] * 167
    coin = normalize_coin({"symbol": "X", "closes_1h": closes})
    assert coin["chart_dist_7d_pct"] == pytest.approx(coin["chart_dist_30d_pct"])
    assert coin["chart_dist_7d_pct"] == pytest.approx(closes_pct_from_high(closes[-168:]))
    assert len(coin["spark_closes_7d"]) == 168
    assert len(coin["spark_closes_30d"]) == 720


def test_hourly_dist_diverges_when_older_high() -> None:
    closes = [50.0] + [10.0] * 551 + [20.0] + [15.0] * 167
    coin = normalize_coin({"symbol": "Y", "closes_1h": closes})
    assert coin["chart_dist_30d_pct"] != coin["chart_dist_7d_pct"]


def test_strategy_sheet_sorted_by_net_including_bh() -> None:
    rows = strategy_sheet_rows(
        {
            "backtest_top_strategies": [
                {"indicator": "LOW", "net_pct": 2.0, "trades": 10, "tsl_hits": 2},
                {"indicator": "HIGH", "net_pct": 20.0, "trades": 10, "tsl_hits": 2},
                {"indicator": "MID", "net_pct": 8.0, "trades": 10, "tsl_hits": 2},
            ],
            "backtest_buy_hold": {"indicator": "B&H", "net_pct": 10.0},
        }
    )
    assert [r["indicator"] for r in rows] == ["HIGH", "B&H", "MID", "LOW"]
    assert [r["net_pct"] for r in rows] == [20.0, 10.0, 8.0, 2.0]


def test_watch_column_checkbox(qtbot: QtBot) -> None:
    table = read_only_table(S.SCANNER_LTS_HEADERS, S.SCANNER_TITLE)
    qtbot.addWidget(table)
    fill_lts_table(
        table,
        [{"symbol": "BTC", "pair": "BTC/USD", "listed_on": ["kraken"]}],
        compare=set(),
        watch={"BTC/USD"},
        on_watch=lambda _p, _c: None,
    )
    assert table.columnCount() == COLUMNS
    host = table.cellWidget(0, COL_WATCH)
    assert host is not None
    box = host.findChild(QCheckBox)
    assert box is not None
    assert box.isChecked()


def test_header_chevron_on_active_sort(qtbot: QtBot) -> None:
    from trendalgo.device.scanner_sort import header_label

    assert header_label("Health", active=True, direction=-1).endswith("▼")
    assert header_label("Health", active=True, direction=1).endswith("▲")
    assert header_label("Health", active=False, direction=-1) == "Health"
    table = read_only_table(S.SCANNER_LTS_HEADERS, S.SCANNER_TITLE)
    qtbot.addWidget(table)
    fill_lts_table(
        table,
        [{"symbol": "BTC", "pair": "BTC/USD", "listed_on": ["kraken"]}],
        compare=set(),
        sort_key="health",
        sort_dir=-1,
    )
    item = table.horizontalHeaderItem(11)
    assert item is not None
    assert "▼" in item.text()


def test_spark_gain_color(qtbot: QtBot) -> None:
    from trendalgo.device.views.sparkline import Sparkline

    widget = Sparkline()
    qtbot.addWidget(widget)
    widget.set_values([1.0, 2.0], gain=5.0)
    assert widget._gain == 5.0
    widget.set_values([2.0, 1.0], gain=-3.0)
    assert widget._gain == -3.0


def test_results_sheet_cells() -> None:
    from trendalgo.device import strings as S
    from trendalgo.device.backtest_results_ui import row_cells

    headers = S.BACKTEST_RESULT_HEADERS
    assert "Strategy" not in headers
    assert "Equity" not in headers
    cells = row_cells(
        {
            "indicator": "RSI",
            "strategy": "mean",
            "timeframe": "1h",
            "params": {"period": 14},
            "trailing_stop_pct": 8,
            "net_pct": 12.0,
            "fees_paid": 26.0,
            "win_pct": 55.0,
            "trades": 10,
            "tsl_hits": 2,
            "final_equity": 1120.0,
        },
        is_bh=False,
    )
    assert cells[0].startswith("RSI")
    assert cells[1] == "1h"
    assert cells[4] == "26.00"
    assert cells[5] == "0"  # open
    assert cells[6] == "6"  # wins (55% of 10)
    assert cells[7] == "4"  # losses
    assert cells[10] == "2"
    assert "20" in cells[11]  # tsl hit %
    assert cells[12]  # Strength
    # Create Bot is a widget column, not a text cell.
    assert len(cells) == len(headers) - 1
    assert headers[-1]
    bh = row_cells({"indicator": "B&H", "net_pct": 4.0, "fees_paid": 5.2}, is_bh=True)
    assert bh[4] == "5.20"
    assert bh[5] == "—"  # Open
    assert bh[9] == "—"  # TSL
    assert bh[10] == "—"  # TSL hits
    assert bh[12] == "—"  # Strength


def test_results_heatmap_ranks_tsl_inverted() -> None:
    from trendalgo.device.backtest_results_ui import heat_for_rows

    rows = [
        {"indicator": "A", "net_pct": 10.0, "win_pct": 80.0, "trades": 5, "tsl_hits": 1},
        {"indicator": "B", "net_pct": 50.0, "win_pct": 40.0, "trades": 20, "tsl_hits": 10},
        {"indicator": "B&H", "net_pct": 5.0, "win_pct": 0.0, "trades": 1},
    ]
    heat = heat_for_rows(rows)
    # Best net (50) greener than worst (5): green channel higher at end of #RRGGBB
    assert heat[3][1] is not None and heat[3][2] is not None
    assert int(heat[3][1][3:5], 16) > int(heat[3][2][3:5], 16)
    # More TSL hits → redder (invert): few hits greener
    assert heat[10][0] is not None and heat[10][1] is not None
    assert int(heat[10][0][3:5], 16) > int(heat[10][1][3:5], 16)
    # B&H has no TSL color
    assert heat[10][2] is None
    # More wins greener (B has 8 wins, A has 4)
    assert heat[6][0] is not None and heat[6][1] is not None
    assert int(heat[6][1][3:5], 16) > int(heat[6][0][3:5], 16)
    # Fewer losses greener (A has 1 loss, B has 12)
    assert heat[7][0] is not None and heat[7][1] is not None
    assert int(heat[7][0][3:5], 16) > int(heat[7][1][3:5], 16)
