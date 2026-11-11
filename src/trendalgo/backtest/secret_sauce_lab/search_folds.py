"""Train/holdout fold helpers for Secret Sauce search (SIM-05)."""

from __future__ import annotations

from typing import Iterable

import numpy as np


def bar_folds(
    n: int,
    *,
    holdout_frac: float = 0.35,
    purge_bars: int = 0,
) -> tuple[list[int], list[int]]:
    """Causal time split: train prefix, purged gap, holdout suffix."""
    if n < 4:
        return list(range(n)), []
    hold_n = max(1, int(n * holdout_frac))
    train_end = max(1, n - hold_n)
    purge = max(0, int(purge_bars))
    train = list(range(0, max(1, train_end - purge)))
    hold = list(range(min(n, train_end + purge), n))
    if not hold:
        hold = [n - 1]
        train = list(range(0, n - 1)) or [0]
    return train, hold


def passes_holdout_gate(train_net: float, holdout_net: float) -> bool:
    """Require positive holdout that keeps ≥60% of train net."""
    return holdout_net > 0.0 and holdout_net > 0.6 * train_net


def restrict_mask(mask: np.ndarray, allowed: Iterable[int]) -> np.ndarray:
    allow = set(int(i) for i in allowed)
    out = np.asarray(mask, dtype=bool).copy()
    for i in range(len(out)):
        if i not in allow:
            out[i] = False
    return out
