"""Scanner full-parity helpers: chart dist, sort, filters, pin, Results."""

from __future__ import annotations

import os

import pytest

from trendalgo.device.lts_scan_model import closes_pct_from_high, filter_coins, normalize_coin
from trendalgo.device.scanner_sort import sort_coins

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

from PySide6.QtWidgets import QCheckBox, QPushButton  # noqa: E402
from pytestqt.qtbot import QtBot  # noqa: E402

from trendalgo.device import strings as S  # noqa: E402
from trendalgo.device.views.scanner_table import (  # noqa: E402
    COL_RESULTS,
    COL_WATCH,
    fill_lts_table,
)
from trendalgo.device.views.widgets import read_only_table  # noqa: E402


def test_closes_pct_from_high() -> None:
    assert closes_pct_from_high([100.0, 90.0, 80.0]) == pytest.approx(20.0)
    assert closes_pct_from_high([10.0]) is None
    assert closes_pct_from_high([]) is None


def test_normalize_stores_chart_dist() -> None:
    coin = normalize_coin(
        {
            "symbol": "BTC",
            "closes_1h": [100.0] * 10 + [80.0],
            "closes_1d": [50.0, 40.0],
        }
    )
    assert coin["chart_dist_7d_pct"] == pytest.approx(20.0)
    assert coin["chart_dist_30d_pct"] == pytest.approx(20.0)


def test_filter_excludes_high_chart_dist() -> None:
    coins = [
        normalize_coin({"symbol": "A", "closes_1h": [100.0, 95.0], "listed_on": ["kraken"]}),
        normalize_coin({"symbol": "B", "closes_1h": [100.0, 80.0], "listed_on": ["kraken"]}),
    ]
    kept = filter_coins(coins, chart_dist_max_7d=10.0)
    assert [c["symbol"] for c in kept] == ["A"]


def test_sort_health_desc() -> None:
    coins = [
        {"symbol": "A", "health_score": 40.0},
        {"symbol": "B", "health_score": 90.0},
        {"symbol": "C", "health_score": 70.0},
    ]
    ordered = sort_coins(coins, key="health", direction=-1)
    assert [c["symbol"] for c in ordered] == ["B", "C", "A"]


def test_pin_shows_pressed(qtbot: QtBot) -> None:
    table = read_only_table(S.SCANNER_LTS_HEADERS, S.SCANNER_TITLE)
    qtbot.addWidget(table)
    fill_lts_table(
        table,
        [{"symbol": "BTC", "pair": "BTC/USD", "listed_on": ["kraken"]}],
        compare=set(),
        watch={"BTC/USD"},
        on_watch=lambda _p, _c: None,
    )
    host = table.cellWidget(0, COL_WATCH)
    assert host is not None
    box = host.findChild(QCheckBox)
    assert box is not None
    assert box.isChecked()


def test_results_enabled_after_merge_fields(qtbot: QtBot) -> None:
    table = read_only_table(S.SCANNER_LTS_HEADERS, S.SCANNER_TITLE)
    qtbot.addWidget(table)
    fill_lts_table(
        table,
        [
            {
                "symbol": "ETH",
                "pair": "ETH/USD",
                "bot_best_net_pct": 55.0,
                "backtest_top_strategies": [{"name": "x"}],
                "listed_on": ["kraken"],
            }
        ],
        compare=set(),
    )
    btn = table.cellWidget(0, COL_RESULTS)
    assert isinstance(btn, QPushButton)
    assert btn.isEnabled()
