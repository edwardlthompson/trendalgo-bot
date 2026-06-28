"""Tests for fleet pass-3 TSL sweep."""

from trendalgo.backtest.fleet_config import TSL_SWEEP_PCTS
from trendalgo.backtest.fleet_tsl_optimize import estimate_tsl_combos


def test_tsl_sweep_range() -> None:
    assert TSL_SWEEP_PCTS == tuple(i / 100.0 for i in range(0, 21, 2))
    assert len(TSL_SWEEP_PCTS) == 11


def test_estimate_tsl_combos() -> None:
    rows = [{"strategy_id": "RSI", "timeframe": "60"} for _ in range(3)]
    assert estimate_tsl_combos(rows) == 3 * len(TSL_SWEEP_PCTS)
