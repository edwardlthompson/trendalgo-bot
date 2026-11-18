"""SIM-01: next-bar fills via fill_offset (default 1; 0 keeps parity)."""

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


def _ohlc(closes: list[float]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "open": closes,
            "high": closes,
            "low": closes,
            "close": closes,
            "volume": [1.0] * len(closes),
        }
    )


def test_fill_offset_zero_parity_signal_bar_close() -> None:
    closes = [100.0, 100.0, 101.0, 101.0]
    df = _ohlc(closes)
    entries = np.array([False, True, False, False])
    exits = np.array([False, False, True, False])
    stats = simulate_long_with_fees(df, entries, exits, stake_usd=1000.0, fee=_fee(), fill_offset=0)
    assert stats["trades"] == 1
    assert stats["gross_profit"] == 10.0


def test_fill_offset_default_shifts_entry_one_percent() -> None:
    # Signal at i=1 (close 100); next bar close is 101 → +1% entry vs signal close.
    closes = [100.0, 100.0, 101.0, 110.0]
    df = _ohlc(closes)
    entries = np.array([False, True, False, False])
    exits = np.array([False, False, False, True])
    zero = simulate_long_with_fees(
        df, entries, exits, stake_usd=1000.0, fee=_fee(), fill_offset=0, collect_trades=True
    )
    one = simulate_long_with_fees(
        df, entries, exits, stake_usd=1000.0, fee=_fee(), collect_trades=True
    )
    assert one["trades"] == 1
    entry0 = float(zero["trade_list"][0]["entry_price"])
    entry1 = float(one["trade_list"][0]["entry_price"])
    assert entry0 == 100.0
    assert entry1 == 101.0
    assert abs(entry1 / entry0 - 1.01) < 1e-9
