"""SIM-02: slippage both sides; intrabar stops; gap-through worse fill."""

from __future__ import annotations

import numpy as np
import pandas as pd

from trendalgo.backtest.ta_simulator import simulate_long_with_fees
from trendalgo.exchanges.fees import ExchangeFeeSchedule


def _fee() -> ExchangeFeeSchedule:
    return ExchangeFeeSchedule(
        exchange_id="test",
        taker_pct=0.0,
        maker_pct=0.0,
        tier="retail",
        source_url="",
    )


def test_slippage_bps_both_sides_worsens_round_trip() -> None:
    df = pd.DataFrame(
        {
            "open": [100.0, 100.0, 110.0, 110.0],
            "high": [100.0, 100.0, 110.0, 110.0],
            "low": [100.0, 100.0, 110.0, 110.0],
            "close": [100.0, 100.0, 110.0, 110.0],
            "volume": [1.0] * 4,
        }
    )
    entries = np.array([False, True, False, False])
    exits = np.array([False, False, True, False])
    clean = simulate_long_with_fees(df, entries, exits, stake_usd=1000.0, fee=_fee(), fill_offset=0)
    slip = simulate_long_with_fees(
        df,
        entries,
        exits,
        stake_usd=1000.0,
        fee=_fee(),
        fill_offset=0,
        slippage_bps=100.0,  # 1% each side
    )
    assert clean["gross_profit"] == 100.0
    assert slip["gross_profit"] < clean["gross_profit"]
    # entry 101, exit 108.9 → ~78.2 on 1000 stake
    assert abs(slip["gross_profit"] - (1000.0 * (108.9 / 101.0 - 1.0))) < 0.05


def test_wick_touch_stop_recovers_still_stops() -> None:
    # Peak 120, 10% TSL → stop 108. Low wicks to 107 then close recovers to 115.
    df = pd.DataFrame(
        {
            "open": [100.0, 100.0, 120.0, 115.0],
            "high": [100.0, 100.0, 120.0, 116.0],
            "low": [100.0, 100.0, 119.0, 107.0],
            "close": [100.0, 100.0, 120.0, 115.0],
            "volume": [1.0] * 4,
        }
    )
    entries = np.array([False, True, False, False])
    exits = np.array([False, False, False, False])
    stats = simulate_long_with_fees(
        df,
        entries,
        exits,
        stake_usd=1000.0,
        fee=_fee(),
        trailing_stop_pct=0.10,
        fill_offset=0,
        collect_trades=True,
    )
    assert stats["tsl_hits"] == 1
    assert stats["trades"] == 1
    assert float(stats["trade_list"][0]["exit_price"]) <= 108.0


def test_gap_down_fills_below_stop() -> None:
    # Peak 100, 5% stop → 95. Bar opens at 90 (gap through).
    df = pd.DataFrame(
        {
            "open": [100.0, 100.0, 100.0, 90.0],
            "high": [100.0, 100.0, 100.0, 91.0],
            "low": [100.0, 100.0, 100.0, 89.0],
            "close": [100.0, 100.0, 100.0, 90.5],
            "volume": [1.0] * 4,
        }
    )
    entries = np.array([False, True, False, False])
    exits = np.array([False, False, False, False])
    stats = simulate_long_with_fees(
        df,
        entries,
        exits,
        stake_usd=1000.0,
        fee=_fee(),
        trailing_stop_pct=0.05,
        fill_offset=0,
        collect_trades=True,
    )
    assert stats["tsl_hits"] == 1
    assert float(stats["trade_list"][0]["exit_price"]) == 90.0
