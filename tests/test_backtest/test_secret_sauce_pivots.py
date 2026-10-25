"""Causal pivot features for Secret Sauce Lab."""

from __future__ import annotations

import numpy as np

from trendalgo.backtest.secret_sauce_pivots import PIVOT_KEYS, merge_pivot_features_into_rows


def test_merge_pivot_features_keys() -> None:
    n = 60
    closes = np.linspace(100, 110, n)
    highs = closes + 1
    lows = closes - 1
    vols = np.full(n, 1000.0)
    rows: list[dict[str, float]] = [{} for _ in range(n)]
    merge_pivot_features_into_rows(closes, highs, lows, rows, volumes=vols)
    assert all(key in rows[-1] for key in PIVOT_KEYS)
    assert rows[-1]["pivot_dist_pp"] != 0.0 or rows[-1]["pivot_dist_s1"] != 0.0
