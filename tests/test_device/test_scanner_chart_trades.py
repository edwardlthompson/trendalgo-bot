"""Scanner chart trade overlay helpers."""

from __future__ import annotations

import numpy as np
import pandas as pd

from trendalgo.backtest.ta_simulator import simulate_long_with_fees, trade_hold_regions
from trendalgo.device.scanner_all_ta_prune import DEEPEN_TSL_PCTS
from trendalgo.device.scanner_chart_trades import (
    _tsl_fraction,
    frame_from_closes,
    overlay_net_pct,
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
