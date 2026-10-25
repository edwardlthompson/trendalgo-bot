"""Pivot gates for Sauce TA coincidence masks."""

from __future__ import annotations

import numpy as np
import pandas as pd

from trendalgo.backtest.secret_sauce_pivot_gate import refine_masks_with_pivots
from trendalgo.exchanges.fees import ExchangeFeeSchedule


def _fee() -> ExchangeFeeSchedule:
    return ExchangeFeeSchedule(
        exchange_id="test", taker_pct=0.0, maker_pct=0.0, tier="retail", source_url=""
    )


def test_refine_masks_returns_baseline_when_no_lift() -> None:
    n = 64
    idx = pd.date_range("2024-01-01", periods=n, freq="h", tz="UTC")
    close = np.linspace(100, 108, n)
    df = pd.DataFrame(
        {
            "open": close,
            "high": close + 0.5,
            "low": close - 0.5,
            "close": close,
            "volume": np.full(n, 1000.0),
        },
        index=idx,
    )
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    entries[10] = True
    entries[30] = True
    exits[20] = True
    exits[40] = True
    e2, x2, stats, tag = refine_masks_with_pivots(
        df,
        entries,
        exits,
        entry_labels=[10, 30],
        exit_labels=[20, 40],
        fee=_fee(),
        stake=1000.0,
        trailing_stop_pct=0.0,
    )
    assert e2.shape == entries.shape
    assert x2.shape == exits.shape
    assert "net_profit" in stats
    assert tag is None or isinstance(tag, str)
