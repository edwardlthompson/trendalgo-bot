"""Trade pool excludes chart/math helpers that still live in the full TA library."""

from __future__ import annotations

from trendalgo.ta.catalog import all_ta_names
from trendalgo.ta.strategy_pool import (
    is_reference_function,
    is_trade_strategy,
    reference_pool_names,
    trade_strategy_names,
)


def test_math_and_atr_are_reference_not_trade() -> None:
    for sid in ("ADD", "ACOS", "ATR", "NATR", "BETA", "TYPPRICE", "HT_SINE"):
        assert is_reference_function(sid)
        assert not is_trade_strategy(sid)


def test_core_trade_strategies_remain() -> None:
    for sid in ("RSI", "MACD", "BBANDS", "SMA", "SAR", "ADX", "OBV", "CDLENGULFING"):
        assert is_trade_strategy(sid)


def test_pools_partition_catalog() -> None:
    trade = set(trade_strategy_names())
    ref = set(reference_pool_names())
    all_names = set(all_ta_names())
    assert trade.isdisjoint(ref)
    assert trade | ref == all_names
    assert len(trade) < len(all_names)
    assert len(ref) >= 40
