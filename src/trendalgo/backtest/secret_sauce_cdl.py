"""Causal CDL pattern fire features (Q/USD beaters first, then common set)."""

from __future__ import annotations

import numpy as np
import pandas as pd

# Priority: patterns that beat Sauce on Q/USD, then high-signal classics.
CDL_PRIORITY = (
    "CDLDOJISTAR",
    "CDLSIDEGAP3METHODS",
    "CDLTAKURI",
    "CDLENGULFING",
    "CDLHAMMER",
    "CDLSHOOTINGSTAR",
    "CDLMORNINGSTAR",
    "CDLEVENINGSTAR",
    "CDL3WHITESOLDIERS",
    "CDL3BLACKCROWS",
    "CDLPIERCING",
    "CDLDARKCLOUDCOVER",
    "CDLHARAMI",
    "CDLDOJI",
)


def cdl_feature_keys() -> tuple[str, ...]:
    return tuple(f"cdl_{name.lower()}" for name in CDL_PRIORITY)


def merge_cdl_into_rows(df: pd.DataFrame, rows: list[dict[str, float]]) -> None:
    """Append binary CDL fire columns (nonzero TA-Lib integer → 1.0). Soft-skip failures."""
    if not rows or df.empty:
        return
    from trendalgo.ta.engine import compute

    n = len(rows)
    for name in CDL_PRIORITY:
        key = f"cdl_{name.lower()}"
        try:
            out = compute(name, df)
        except (TypeError, ValueError, KeyError, AttributeError):
            continue
        series = _primary(out)
        if series is None or len(series) != n:
            continue
        for i, row in enumerate(rows):
            val = float(series[i]) if np.isfinite(series[i]) else 0.0
            row[key] = 1.0 if abs(val) > 1e-9 else 0.0


def _primary(out: dict[str, np.ndarray]) -> np.ndarray | None:
    if not out:
        return None
    for key in ("integer", "CDL", "real"):
        if key in out:
            return np.asarray(out[key], dtype=float)
    first = next(iter(out.values()), None)
    return None if first is None else np.asarray(first, dtype=float)
