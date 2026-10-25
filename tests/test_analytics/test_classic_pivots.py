"""Classic pivot formulas and causal prior-period window."""

from __future__ import annotations

import numpy as np

from trendalgo.analytics.classic_pivots import (
    classic_levels,
    compute_pivot_set,
    prior_period_hlc,
)


def test_classic_levels_known_hlc() -> None:
    # H=12 L=10 C=11 → PP=11; R1=12; S1=10
    levels = classic_levels(12.0, 10.0, 11.0)
    assert levels["PP"] == 11.0
    assert levels["R1"] == 12.0
    assert levels["S1"] == 10.0
    assert levels["R2"] == 13.0
    assert levels["S2"] == 9.0


def test_prior_period_excludes_current_bar() -> None:
    closes = np.arange(1.0, 31.0)
    highs = closes + 1.0
    lows = closes - 1.0
    hlc = prior_period_hlc(highs, lows, closes, period_bars=5)
    assert hlc is not None
    h, low_v, c = hlc
    # Window is bars [24..29) indexes 24..28 → closes 25..29; current bar 30 excluded
    assert c == 29.0
    assert h == 30.0  # high of close 29 = 30
    assert low_v == 24.0  # low of close 25 = 24


def test_compute_pivot_set_ok() -> None:
    rng = np.random.default_rng(0)
    n = 80
    closes = 100 + np.cumsum(rng.normal(0, 0.5, n))
    highs = closes + 1
    lows = closes - 1
    pivots = compute_pivot_set(highs, lows, closes, period_bars=24)
    assert pivots is not None
    assert len(pivots.levels) == 7
    names = {level.name for level in pivots.levels}
    assert names == {"R3", "R2", "R1", "PP", "S1", "S2", "S3"}
