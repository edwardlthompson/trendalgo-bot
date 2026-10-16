"""Indicator Strength: Wilson LB × TSL-exit quality."""

from __future__ import annotations

from trendalgo.device.indicator_strength import (
    indicator_strength,
    strength_from_row,
    wilson_lower_bound,
)


def test_wilson_few_wins_below_many() -> None:
    two = wilson_lower_bound(2, 2)
    twenty = wilson_lower_bound(20, 20)
    assert 0.0 < two < twenty < 1.0


def test_strength_rewards_sample_size_and_penalizes_tsl() -> None:
    lucky = indicator_strength(trades=2, wins=2, tsl_hits=0)
    solid = indicator_strength(trades=20, wins=20, tsl_hits=0)
    tsl_bailout = indicator_strength(trades=20, wins=20, tsl_hits=14)
    assert lucky is not None and solid is not None and tsl_bailout is not None
    assert lucky < solid
    assert tsl_bailout < solid
    assert tsl_bailout < lucky


def test_strength_from_row_none_without_trades() -> None:
    assert strength_from_row({"indicator": "RSI", "trades": 0, "win_pct": 100}) is None
    assert strength_from_row({"indicator": "B&H", "trades": 10, "win_pct": 100}) is None
    score = strength_from_row({"indicator": "RSI", "trades": 10, "win_pct": 80.0, "tsl_hits": 0})
    assert score is not None and score > 0
