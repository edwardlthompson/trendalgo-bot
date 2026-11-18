"""SIM-05: holdout is a selection constraint, not post-hoc only."""

from __future__ import annotations

import numpy as np

from trendalgo.backtest.secret_sauce_lab.search_folds import (
    bar_folds,
    passes_holdout_gate,
    passes_holdout_gate_soft,
    restrict_mask,
)


def test_passes_holdout_gate_requires_positive_and_ratio() -> None:
    assert passes_holdout_gate(100.0, 70.0)
    assert not passes_holdout_gate(100.0, 50.0)
    assert not passes_holdout_gate(100.0, -1.0)


def test_passes_holdout_gate_soft_ladder() -> None:
    assert passes_holdout_gate_soft(100.0, 55.0)
    assert not passes_holdout_gate_soft(100.0, 40.0)
    assert not passes_holdout_gate_soft(100.0, -1.0)


def test_bar_folds_purge_gap() -> None:
    train, hold = bar_folds(100, holdout_frac=0.35, purge_bars=4)
    assert max(train) < min(hold)
    assert min(hold) - max(train) > 1


def test_restrict_mask_zeros_outside_fold() -> None:
    mask = np.array([True, True, True, True])
    out = restrict_mask(mask, [0, 3])
    assert list(out) == [True, False, False, True]
