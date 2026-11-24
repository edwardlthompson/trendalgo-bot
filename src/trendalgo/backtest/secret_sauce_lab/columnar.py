"""Columnar causal feature matrix for fast Lab masks."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from trendalgo.backtest.oracle_pattern_mine import RuleConjunct
from trendalgo.backtest.secret_sauce_feature_cache import get_cached_feature_matrix
from trendalgo.backtest.secret_sauce_features import causal_features


def feature_matrix(df: pd.DataFrame) -> tuple[dict[str, np.ndarray], list[dict[str, float]]]:
    """Build or reuse cached name→float array map from causal_features (one pass)."""
    return get_cached_feature_matrix(df, causal_features)


def mask_conjuncts(
    cols: dict[str, np.ndarray], conjuncts: tuple[RuleConjunct, ...] | Any
) -> np.ndarray:
    n = len(next(iter(cols.values()))) if cols else 0
    if n == 0 or not conjuncts:
        return np.zeros(n, dtype=bool)
    m = np.ones(n, dtype=bool)
    for c in conjuncts:
        arr = cols.get(c.feature)
        if arr is None:
            return np.zeros(n, dtype=bool)
        if c.op == ">=":
            m &= arr >= c.value
        elif c.op == "<=":
            m &= arr <= c.value
        else:
            return np.zeros(n, dtype=bool)
    return m
