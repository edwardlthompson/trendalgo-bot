"""Scanner All-TA vs 3Commas signal set + Results asterisk."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

from trendalgo.device.scanner_all_ta_bt import fleet_row_to_lts  # noqa: E402
from trendalgo.device.scanner_signal_sets import (  # noqa: E402
    BT_SET_3COMMAS,
    BT_SET_ALL_TA,
    THREE_COMMAS_CATALOG_IDS,
    is_three_commas_indicator,
    normalize_bt_signal_set,
)
from trendalgo.device.views.scanner_results import indicator_display_label  # noqa: E402


def test_normalize_bt_signal_set_defaults_to_3commas() -> None:
    assert normalize_bt_signal_set(None) == BT_SET_3COMMAS
    assert normalize_bt_signal_set("") == BT_SET_3COMMAS
    assert normalize_bt_signal_set("all_ta") == BT_SET_ALL_TA
    assert normalize_bt_signal_set("All TA") == BT_SET_ALL_TA


def test_is_three_commas_catalog_and_lts_names() -> None:
    assert is_three_commas_indicator("RSI")
    assert is_three_commas_indicator("rsi")
    assert is_three_commas_indicator("EMA Crossover")
    assert is_three_commas_indicator("BBANDS")
    assert "STOCH" in THREE_COMMAS_CATALOG_IDS
    assert not is_three_commas_indicator("SUPERTREND")
    assert not is_three_commas_indicator("B&H")


def test_scan_bt_prefs_persists_bt_signal_set(tmp_path: Path) -> None:
    from trendalgo.device.scan_bt_prefs import ScanBtPrefs, load_scan_bt_prefs, save_scan_bt_prefs

    save_scan_bt_prefs(
        tmp_path,
        ScanBtPrefs(timeframes=["1h"], strategy_denylist=[], bt_signal_set=BT_SET_ALL_TA),
    )
    assert load_scan_bt_prefs(tmp_path).bt_signal_set == BT_SET_ALL_TA
    save_scan_bt_prefs(
        tmp_path,
        ScanBtPrefs(timeframes=["1h"], strategy_denylist=[], bt_signal_set=BT_SET_3COMMAS),
    )
    assert load_scan_bt_prefs(tmp_path).bt_signal_set == BT_SET_3COMMAS


def test_select_bh_beaters_keeps_all_beaters() -> None:
    from trendalgo.device.scanner_all_ta_prune import is_profitable, select_bh_beaters

    rows = [
        {"strategy_id": "A", "net_profit": -10.0},
        {"strategy_id": "B", "net_profit": 5.0},
        {"strategy_id": "C", "net_profit": 20.0},
        {"strategy_id": "D", "net_profit": 8.0},
    ]
    assert not is_profitable(rows[0])
    bh = {"net_profit": 6.0}
    top = select_bh_beaters(rows, bh)
    assert [r["strategy_id"] for r in top] == ["C", "D"]
    assert select_bh_beaters(rows, {"net_profit": 100.0}) == []


def test_strategy_sheet_all_ta_keeps_losers_like_backtest() -> None:
    from trendalgo.device.views.scanner_results import strategy_sheet_rows

    coin = {
        "bt_signal_set": BT_SET_ALL_TA,
        "backtest_buy_hold": {"indicator": "B&H", "net_pct": 10.0},
        "backtest_top_strategies": [
            {"indicator": "RSI", "net_pct": 25.0, "trades": 1},
            {"indicator": "MACD", "net_pct": 8.0, "trades": 4},
            {"indicator": "EMA", "net_pct": 40.0, "trades": 2},
        ],
    }
    rows = strategy_sheet_rows(coin)
    inds = [str(r.get("indicator")) for r in rows]
    assert "MACD" in inds  # below B&H still kept (Backtest parity)
    assert inds[0] == "EMA"
    assert "RSI" in inds
    assert "B&H" in inds


def test_indicator_asterisk_only_for_all_ta() -> None:
    assert indicator_display_label("RSI", bt_signal_set=BT_SET_ALL_TA) == "RSI *"
    assert indicator_display_label("SUPERTREND", bt_signal_set=BT_SET_ALL_TA) == "SUPERTREND"
    assert indicator_display_label("RSI", bt_signal_set=BT_SET_3COMMAS) == "RSI"
    assert "buy & hold" in indicator_display_label("B&H", bt_signal_set=BT_SET_ALL_TA, is_bh=True)


def test_indicator_display_keeps_sauce_ta_and_lab_distinct() -> None:
    from trendalgo.device import strings as S

    ta = indicator_display_label("Secret Sauce TA", bt_signal_set=BT_SET_ALL_TA)
    lab = indicator_display_label("Secret Sauce Lab", bt_signal_set=BT_SET_ALL_TA)
    legacy = indicator_display_label("Secret Sauce", bt_signal_set=BT_SET_ALL_TA)
    assert ta == S.SECRET_SAUCE_TA_LABEL
    assert lab == S.SECRET_SAUCE_LABEL
    assert legacy == S.SECRET_SAUCE_LABEL
    assert ta != lab


def test_fleet_row_to_lts_preserves_net_and_trades() -> None:
    mapped = fleet_row_to_lts(
        {
            "strategy_id": "RSI",
            "timeframe": "1h",
            "params": {"length": 14},
            "trailing_stop_pct": 0.0,
            "net_profit": 50.0,
            "trades": 4,
            "win_rate": 0.75,
            "tsl_hits": 1,
        },
        symbol="BTC",
        stake_usd=1000.0,
    )
    assert mapped["indicator"] == "RSI"
    assert mapped["symbol"] == "BTC"
    assert mapped["net_pct"] == pytest.approx(5.0)
    assert mapped["signal_net_pct"] == pytest.approx(5.0)
    assert mapped["trailing_stop_pct"] == pytest.approx(0.0)
    assert mapped["trades"] == 4
    assert mapped["win_pct"] == pytest.approx(75.0)
    assert mapped["tsl_hits"] == 1


def test_fleet_row_to_lts_derives_win_pct_for_sauce_ta_without_win_rate() -> None:
    """Secret Sauce TA coincidence trials set wins/trades but often omit win_rate."""
    mapped = fleet_row_to_lts(
        {
            "strategy_id": "GEN_SECRET_1",
            "indicator": "Secret Sauce TA",
            "timeframe": "1h",
            "net_profit": 40.0,
            "trades": 8,
            "wins": 6,
            "open_trades": 0,
            "params": {"ss_ta_fee_aware": True},
        },
        symbol="ETH",
        stake_usd=100.0,
    )
    assert mapped["indicator"] == "Secret Sauce TA"
    assert mapped["win_pct"] == pytest.approx(75.0)
    assert mapped["wins"] == 6


def test_merge_routes_all_ta(tmp_path: Path) -> None:
    from trendalgo.device.lts_scan_model import save_filters
    from trendalgo.device.scan_job import _merge_pass1_backtests

    save_filters(tmp_path, {"bt_signal_set": BT_SET_ALL_TA})
    rows: list[dict[str, Any]] = [{"symbol": "BTC", "pair": "BTC/USD"}]
    summary = {
        "results": [
            {
                "indicator": "RSI",
                "timeframe": "1h",
                "params": {},
                "net_pct": 12.0,
                "trades": 3,
                "win_pct": 60.0,
                "symbol": "BTC",
            },
            {
                "indicator": "B&H",
                "timeframe": "1h",
                "params": {},
                "net_pct": 5.0,
                "trades": "-",
                "win_pct": "-",
                "symbol": "BTC",
            },
        ]
    }
    with (
        patch(
            "trendalgo.device.scanner_all_ta_bt.run_all_ta_scan_backtests",
            return_value=summary,
        ) as all_ta,
        patch(
            "trendalgo.lts_vendor.bridge.run_lts_backtest_sweep",
            return_value=summary,
        ) as lts,
    ):
        merged, meta = _merge_pass1_backtests(rows, tmp_path)
    all_ta.assert_called_once()
    lts.assert_not_called()
    assert meta["signal_set"] == BT_SET_ALL_TA
    assert merged[0]["bt_signal_set"] == BT_SET_ALL_TA
    assert merged[0].get("bot_best_net_pct") == pytest.approx(12.0)


def test_merge_routes_3commas_default(tmp_path: Path) -> None:
    from trendalgo.device.lts_scan_model import save_filters
    from trendalgo.device.scan_job import _merge_pass1_backtests

    save_filters(tmp_path, {})
    rows: list[dict[str, Any]] = [{"symbol": "ETH", "pair": "ETH/USD"}]
    summary = {"results": []}
    with (
        patch(
            "trendalgo.device.scanner_all_ta_bt.run_all_ta_scan_backtests",
            return_value=summary,
        ) as all_ta,
        patch(
            "trendalgo.lts_vendor.bridge.run_lts_backtest_sweep",
            return_value=summary,
        ) as lts,
    ):
        merged, meta = _merge_pass1_backtests(rows, tmp_path)
    lts.assert_called_once()
    all_ta.assert_not_called()
    assert meta["signal_set"] == BT_SET_3COMMAS
    assert merged[0]["bt_signal_set"] == BT_SET_3COMMAS
