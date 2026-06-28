"""Tests for fleet param optimization helpers."""

from trendalgo.backtest.fleet_optimize import param_variants


def test_param_variants_rsi() -> None:
    combos = param_variants("RSI", max_variants=10)
    assert len(combos) >= 1
    assert "timeperiod" in combos[0]


def test_param_variants_cdl_empty_params() -> None:
    combos = param_variants("CDLDOJI", max_variants=5)
    assert len(combos) == 1
