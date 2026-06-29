"""Tests for fee-aware TA simulator."""

import numpy as np
import pandas as pd

from trendalgo.backtest.ta_simulator import simulate_buy_and_hold, simulate_long_with_fees
from trendalgo.exchanges.fees import get_fee_schedule


def _df(closes: list[float]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "timestamp_ms": list(range(len(closes))),
            "open": closes,
            "high": closes,
            "low": closes,
            "close": closes,
            "volume": [1.0] * len(closes),
        }
    )


def test_simulate_buy_and_hold() -> None:
    closes = [100.0, 105.0, 110.0]
    df = _df(closes)
    fee = get_fee_schedule("kraken")
    stats = simulate_buy_and_hold(df, stake_usd=1000.0, fee=fee)
    assert stats is not None
    assert stats["trades"] == 1
    assert stats["gross_profit"] == 100.0
    assert stats["strategy_id"] == "BUY_AND_HOLD"


def test_simulate_long_with_fees_known_trade() -> None:
    closes = [100.0, 100.0, 101.0, 101.0]
    df = _df(closes)
    entries = np.array([False, True, False, False])
    exits = np.array([False, False, True, False])
    fee = get_fee_schedule("kraken")
    stats = simulate_long_with_fees(df, entries, exits, stake_usd=1000.0, fee=fee)
    assert stats["trades"] == 1
    assert stats["tsl_hits"] == 0
    assert stats["gross_profit"] == 10.0
    assert stats["fees_paid"] == 5.2
    assert stats["net_profit"] == 4.8


def test_simulate_long_with_fees_counts_tsl_hits() -> None:
    closes = [100.0, 100.0, 110.0, 115.0, 100.0]
    df = _df(closes)
    entries = np.array([False, True, False, False, False])
    exits = np.array([False, False, False, False, False])
    fee = get_fee_schedule("kraken")
    stats = simulate_long_with_fees(
        df,
        entries,
        exits,
        stake_usd=1000.0,
        fee=fee,
        trailing_stop_pct=0.10,
    )
    assert stats["trades"] == 1
    assert stats["tsl_hits"] == 1
