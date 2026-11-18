"""Scanner chart trade overlay helpers."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from trendalgo.backtest.ta_simulator import simulate_long_with_fees, trade_hold_regions
from trendalgo.device.scanner_all_ta_prune import DEEPEN_TSL_PCTS
from trendalgo.device.scanner_chart_trades import (
    _normalize_tf,
    _tsl_fraction,
    attach_path_envelopes,
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
        fill_offset=0,  # region helper parity — not next-bar fill semantics
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
        fill_offset=0,
    )
    clipped = simulate_long_with_fees(
        df,
        entries,
        exits,
        stake_usd=1000.0,
        fee=fee,
        trailing_stop_pct=0.01,
        collect_trades=True,
        fill_offset=0,
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


def test_overlay_net_pct_prefers_fee_aware_net_pnl() -> None:
    # Gross pnl_pct would sum to 10; fee-aware net_pnl/stake is 4.8.
    regions = [
        {"pnl_pct": 6.0, "net_pnl": 30.0},
        {"pnl_pct": 4.0, "net_pnl": 18.0},
    ]
    assert overlay_net_pct(regions, stake_usd=1000.0) == 4.8


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


def test_oracle_swings_keep_trough_peak_prices_not_closes() -> None:
    """Oracle enters at bar low / exits at bar high — overlays must not rewrite to close."""
    idx = pd.date_range("2026-10-01", periods=40, freq="h", tz="UTC")
    close = pd.Series(np.linspace(80_000.0, 82_000.0, 40), index=idx)
    df = pd.DataFrame(
        {
            "open": close,
            "high": close + 800.0,
            "low": close - 800.0,
            "close": close,
            "volume": 1.0,
        },
        index=idx,
    )
    entry_i, exit_i = 8, 25
    swings = [
        {
            "entry_index": entry_i,
            "exit_index": exit_i,
            "entry_time": str(idx[entry_i]),
            "exit_time": str(idx[exit_i]),
            "entry_price": float(df["low"].iloc[entry_i]),
            "exit_price": float(df["high"].iloc[exit_i]),
            "pnl_pct": 3.5,
            "net_pnl": 35.0,
        }
    ]
    regions = regions_from_oracle_swings(df, swings)
    assert len(regions) == 1
    assert regions[0]["entry_price"] == pytest.approx(float(df["low"].iloc[entry_i]))
    assert regions[0]["exit_price"] == pytest.approx(float(df["high"].iloc[exit_i]))
    # Must not silently substitute closes (that floats bands off the swing extremes).
    assert regions[0]["entry_price"] != pytest.approx(float(df["close"].iloc[entry_i]))


def test_oracle_swings_remap_indexes_by_timestamp_on_shifted_frame() -> None:
    """When the chart frame rolls forward, keep swing prices — do not use stale indexes."""
    idx = pd.date_range("2026-10-01", periods=50, freq="h", tz="UTC")
    close = pd.Series(np.linspace(80_000.0, 85_000.0, 50), index=idx)
    scan = pd.DataFrame(
        {
            "open": close,
            "high": close + 500.0,
            "low": close - 500.0,
            "close": close,
            "volume": 1.0,
        },
        index=idx,
    )
    entry_i, exit_i = 10, 30
    entry_px = float(scan["low"].iloc[entry_i])
    exit_px = float(scan["high"].iloc[exit_i])
    swings = [
        {
            "entry_index": entry_i,
            "exit_index": exit_i,
            "entry_time": idx[entry_i].isoformat(),
            "exit_time": idx[exit_i].isoformat(),
            "entry_price": entry_px,
            "exit_price": exit_px,
            "pnl_pct": 4.0,
            "net_pnl": 40.0,
        }
    ]
    # Chart reloads with 5 bars dropped from the left (indexes shift by 5).
    chart = scan.iloc[5:].copy()
    assert chart.index[entry_i] != idx[entry_i]
    regions = regions_from_oracle_swings(chart, swings)
    assert len(regions) == 1
    assert regions[0]["entry_price"] == pytest.approx(entry_px)
    assert regions[0]["exit_price"] == pytest.approx(exit_px)
    # Stale index into the shifted frame would pull the wrong close (~shifted series).
    wrong_close = float(chart["close"].iloc[entry_i])
    assert regions[0]["entry_price"] != pytest.approx(wrong_close)


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


def test_normalize_tf_keeps_8h() -> None:
    assert _normalize_tf("8h") == "8h"
    assert _normalize_tf("8H") == "8h"
    assert _normalize_tf("480") == "8h"
    assert _normalize_tf("1h") == "1h"
    assert _normalize_tf("15m") == "15m"
    assert _normalize_tf("nope") == "1h"


def test_oracle_path_envelope_spans_hold_bars() -> None:
    df = _ohlcv(30)
    swings = [
        {
            "entry_index": 5,
            "exit_index": 12,
            "entry_price": 104.0,
            "exit_price": 113.0,
            "pnl_pct": 8.0,
            "net_pnl": 80.0,
        }
    ]
    regions = regions_from_oracle_swings(df, swings)
    assert len(regions) == 1
    env = regions[0].get("path_envelope")
    assert isinstance(env, list)
    assert len(env) == 8  # bars 5..12 inclusive
    assert regions[0]["entry_time"] == str(df.index[5]) or "2024" in str(regions[0]["entry_time"])


def test_attach_path_envelopes_requires_indexes() -> None:
    df = _ohlcv(20)
    bare = [{"entry_time": "x", "exit_time": "y", "entry_price": 1.0, "exit_price": 2.0}]
    out = attach_path_envelopes(df, bare)
    assert "path_envelope" not in out[0]
    with_idx = [
        {
            "entry_index": 2,
            "exit_index": 6,
            "entry_price": 1.0,
            "exit_price": 2.0,
        }
    ]
    filled = attach_path_envelopes(df, with_idx)
    assert len(filled[0]["path_envelope"]) == 5
