"""Scanner chart trade overlay helpers."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from trendalgo.backtest.ta_simulator import simulate_long_with_fees, trade_hold_regions
from trendalgo.device.scanner_all_ta_prune import DEEPEN_TSL_PCTS
from trendalgo.device.scanner_chart_trades import (
    _tsl_fraction,
    frame_from_closes,
    overlay_net_pct,
    regions_for_strategy,
    regions_from_oracle_swings,
    top_strategy_rows,
)
from trendalgo.exchanges.fees import get_fee_schedule


def test_deepen_tsl_never_zero() -> None:
    assert 0.0 not in DEEPEN_TSL_PCTS
    assert DEEPEN_TSL_PCTS[0] == 0.01
    assert DEEPEN_TSL_PCTS[-1] == 0.20
    assert len(DEEPEN_TSL_PCTS) == 20


def test_collect_trades_and_regions() -> None:
    closes = [100.0, 100.0, 110.0, 105.0]
    index = pd.date_range("2024-01-01", periods=4, freq="h", tz="UTC")
    df = pd.DataFrame(
        {
            "open": closes,
            "high": closes,
            "low": closes,
            "close": closes,
            "volume": [1.0] * 4,
        },
        index=index,
    )
    entries = np.array([False, True, False, False])
    exits = np.array([False, False, False, True])
    fee = get_fee_schedule("kraken")
    stats = simulate_long_with_fees(
        df,
        entries,
        exits,
        stake_usd=1000.0,
        fee=fee,
        collect_trades=True,
    )
    assert stats["trades"] == 1
    trades = stats["trade_list"]
    assert len(trades) == 1
    regions = trade_hold_regions(trades)
    assert len(regions) == 1
    assert regions[0]["profitable"] is True


def test_frame_from_closes_builds_ohlcv() -> None:
    frame = frame_from_closes([100.0, 101.0, 102.0])
    assert len(frame) == 3
    assert list(frame.columns) == ["open", "high", "low", "close", "volume"]


def test_top_strategy_rows_caps_and_skips_bh() -> None:
    coin = {
        "backtest_buy_hold": {"indicator": "B&H", "net_pct": 10},
        "backtest_top_strategies": [
            {"indicator": "B&H", "net_pct": 10},
            {"indicator": "RSI", "net_pct": 12},
            {"indicator": "MACD", "net_pct": 20},
            {"indicator": "EMA", "net_pct": 8},
        ],
    }
    rows = top_strategy_rows(coin, limit=2)
    assert [r["indicator"] for r in rows] == ["MACD", "RSI"]
    all_beaters = top_strategy_rows(coin, limit=None)
    assert [r["indicator"] for r in all_beaters] == ["MACD", "RSI"]


def test_trade_hold_regions_loss_is_not_profitable() -> None:
    regions = trade_hold_regions(
        [
            {
                "entry_time": "2024-01-01T00:00:00+00:00",
                "exit_time": "2024-01-01T04:00:00+00:00",
                "entry_price": 100.0,
                "exit_price": 90.0,
                "net_pnl": -10.5,
                "pnl_pct": -10.5,
                "tsl_exit": True,
            }
        ]
    )
    assert regions[0]["profitable"] is False
    assert regions[0]["tsl_exit"] is True
    assert "TSL" in str(regions[0]["label"])
    assert regions[0]["label"].startswith("-")


def test_tsl_fraction_signal_only_and_percent_units() -> None:
    assert _tsl_fraction({"trailing_stop_pct": 0}) == 0.0
    assert _tsl_fraction({"trailing_stop_pct": 0.0}) == 0.0
    assert _tsl_fraction({}) == 0.0
    assert _tsl_fraction({"trailing_stop_pct": 1}) == 0.01
    assert _tsl_fraction({"trailing_stop_pct": 1.0}) == 0.01
    assert _tsl_fraction({"trailing_stop_pct": 20}) == 0.20
    assert _tsl_fraction({"trailing_stop_pct": 0.05}) == 0.05
    assert _tsl_fraction({"trailing_stop_loss_pct": 3}) == 0.03


def test_signal_only_tsl_does_not_clip_like_one_percent() -> None:
    """Rise then pullback then large move: 1% TSL exits early; signal-only holds."""
    closes = [100.0, 100.0, 120.0, 110.0, 200.0]
    index = pd.date_range("2024-01-01", periods=5, freq="h", tz="UTC")
    df = pd.DataFrame(
        {
            "open": closes,
            "high": closes,
            "low": closes,
            "close": closes,
            "volume": [1.0] * 5,
        },
        index=index,
    )
    entries = np.array([False, True, False, False, False])
    exits = np.array([False, False, False, False, True])
    fee = get_fee_schedule("kraken")
    signal_tsl = _tsl_fraction({"trailing_stop_pct": 0})
    signal = simulate_long_with_fees(
        df,
        entries,
        exits,
        stake_usd=1000.0,
        fee=fee,
        trailing_stop_pct=signal_tsl,
        collect_trades=True,
    )
    clipped = simulate_long_with_fees(
        df,
        entries,
        exits,
        stake_usd=1000.0,
        fee=fee,
        trailing_stop_pct=0.01,
        collect_trades=True,
    )
    assert signal["trades"] == 1
    assert clipped["trades"] == 1
    signal_pct = float(signal["trade_list"][0]["pnl_pct"])
    clipped_pct = float(clipped["trade_list"][0]["pnl_pct"])
    assert signal_pct > 80.0
    assert clipped_pct < 20.0
    assert clipped["trade_list"][0]["tsl_exit"] is True
    assert signal["trade_list"][0]["tsl_exit"] is False


def test_overlay_net_pct_sums_trades() -> None:
    assert overlay_net_pct([{"pnl_pct": 10.0}, {"pnl_pct": -2.5}]) == 7.5
    assert overlay_net_pct([]) is None


def _ohlcv(n: int = 40) -> pd.DataFrame:
    idx = pd.date_range("2024-01-01", periods=n, freq="h", tz="UTC")
    close = pd.Series(range(100, 100 + n), index=idx, dtype=float)
    return pd.DataFrame(
        {
            "open": close,
            "high": close + 1,
            "low": close - 1,
            "close": close,
            "volume": 1.0,
        },
        index=idx,
    )


def test_regions_from_oracle_swings_labels_and_times() -> None:
    df = _ohlcv(30)
    swings = [
        {
            "entry_index": 5,
            "exit_index": 12,
            "entry_price": 105.0,
            "exit_price": 112.0,
            "net_pnl": 50.0,
            "pnl_pct": 6.67,
        }
    ]
    regions = regions_from_oracle_swings(df, swings)
    assert len(regions) == 1
    assert regions[0]["entry_time"]
    assert regions[0]["exit_time"]
    assert regions[0]["label"].startswith("+")
    assert regions[0]["profitable"] is True


def test_regions_for_sauce_ta_uses_coincidence(monkeypatch: pytest.MonkeyPatch) -> None:
    df = _ohlcv(40)
    entries = np.zeros(len(df), dtype=bool)
    exits = np.zeros(len(df), dtype=bool)
    entries[5] = True
    exits[15] = True

    def _fake_prep(_df: pd.DataFrame, sid: str, _params: object) -> tuple:
        if sid == "KDJ":
            return entries, exits, {}
        return None, None, "skip"

    monkeypatch.setattr(
        "trendalgo.device.scanner_chart_trades.prepare_signals",
        _fake_prep,
    )
    row = {
        "indicator": "Secret Sauce TA",
        "timeframe": "1h",
        "ss_coincidence": True,
        "params": {"coincidence_entry": "KDJ", "coincidence_exit": "KDJ"},
        "trailing_stop_pct": 0,
    }
    regions = regions_for_strategy(df, row, stake_usd=1000.0, fee_bps=52.0)
    assert len(regions) >= 1
    assert regions[0].get("label")


def test_regions_for_sauce_lab_gen_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    df = _ohlcv(40)

    def _fake_bt(*_a: object, **_k: object) -> tuple:
        return (
            {
                "trades": 1,
                "trade_list": [
                    {
                        "entry_time": "2024-01-01T05:00:00+00:00",
                        "exit_time": "2024-01-01T15:00:00+00:00",
                        "entry_price": 105.0,
                        "exit_price": 115.0,
                        "net_pnl": 90.0,
                        "pnl_pct": 9.0,
                        "tsl_exit": False,
                    }
                ],
            },
            None,
        )

    monkeypatch.setattr(
        "trendalgo.device.scanner_chart_trades.backtest_one",
        _fake_bt,
    )
    row = {
        "indicator": "Secret Sauce Lab",
        "strategy_id": "GEN_SECRET_1",
        "timeframe": "1h",
        "params": {
            "entry_conjuncts": [{"feature": "rsx16_xup_27", "op": ">=", "value": 1.0}],
            "exit_conjuncts": [{"feature": "rsx10_xdn_80", "op": ">=", "value": 1.0}],
        },
        "heartbeat_dossier": {
            "rule": {
                "strategy_id": "GEN_SECRET_1",
                "conjuncts": [{"feature": "rsx16_xup_27", "op": ">=", "value": 1.0}],
            },
            "exit_rule": {
                "strategy_id": "GEN_SECRET_1",
                "conjuncts": [{"feature": "rsx10_xdn_80", "op": ">=", "value": 1.0}],
            },
            "formula_en": "Enter when rsx. Exit when rsx.",
        },
        "trailing_stop_pct": 0,
    }
    regions = regions_for_strategy(df, row, stake_usd=1000.0, fee_bps=52.0)
    assert len(regions) == 1
    assert "+9.0%" in str(regions[0]["label"])


def test_top_strategy_rows_includes_both_sauces() -> None:
    coin = {
        "backtest_buy_hold": {"indicator": "B&H", "net_pct": 1},
        "backtest_top_strategies": [
            {"indicator": "Secret Sauce TA", "net_pct": 5},
            {"indicator": "Secret Sauce Lab", "net_pct": 8},
            {"indicator": "RSI", "net_pct": 3},
        ],
        "backtest_oracle_max": {"indicator": "Oracle max", "net_pct": 40},
    }
    names = [r["indicator"] for r in top_strategy_rows(coin)]
    assert names[0] == "Secret Sauce Lab"
    assert "Secret Sauce TA" in names
    assert names[-1] == "Oracle max"
