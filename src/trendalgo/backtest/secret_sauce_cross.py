"""Causal oscillator cross-up / cross-down event columns (bounded_reversal math)."""

from __future__ import annotations

import numpy as np

# Binary event keys: 1.0 on the cross bar only (match catalog RSX edge semantics).
RSI_XUP_LEVELS = (15, 20, 23, 25, 28, 30, 32, 35, 40)
RSI_XDN_LEVELS = (60, 65, 68, 70, 72, 75, 80, 85)
STOCH_XUP_LEVELS = (15, 20, 23, 25, 30)
STOCH_XDN_LEVELS = (70, 75, 80, 85)
RSX_XUP_LEVELS = RSI_XUP_LEVELS
RSX_XDN_LEVELS = RSI_XDN_LEVELS

CROSS_KEYS: tuple[str, ...] = tuple(
    [f"rsi_xup_{lv}" for lv in RSI_XUP_LEVELS]
    + [f"rsi_xdn_{lv}" for lv in RSI_XDN_LEVELS]
    + [f"stoch_xup_{lv}" for lv in STOCH_XUP_LEVELS]
    + [f"stoch_xdn_{lv}" for lv in STOCH_XDN_LEVELS]
    + [f"rsx_xup_{lv}" for lv in RSX_XUP_LEVELS]
    + [f"rsx_xdn_{lv}" for lv in RSX_XDN_LEVELS]
)


def cross_up(series: np.ndarray, level: float) -> np.ndarray:
    """True on bars where series crosses up through level (prev < level <= curr)."""
    n = len(series)
    out = np.zeros(n, dtype=float)
    if n < 2:
        return out
    prev = series[:-1]
    curr = series[1:]
    hits = (prev < level) & (curr >= level)
    out[1:] = hits.astype(float)
    return out


def cross_down(series: np.ndarray, level: float) -> np.ndarray:
    """True on bars where series crosses down through level (prev > level >= curr)."""
    n = len(series)
    out = np.zeros(n, dtype=float)
    if n < 2:
        return out
    prev = series[:-1]
    curr = series[1:]
    hits = (prev > level) & (curr <= level)
    out[1:] = hits.astype(float)
    return out


def osc_cross_columns(
    rsi_a: np.ndarray, stoch_a: np.ndarray, rsx_a: np.ndarray | None = None
) -> dict[str, np.ndarray]:
    """Name → float array (0/1) for RSI/stoch/RSX cross events."""
    cols: dict[str, np.ndarray] = {}
    for lv in RSI_XUP_LEVELS:
        cols[f"rsi_xup_{lv}"] = cross_up(rsi_a, float(lv))
    for lv in RSI_XDN_LEVELS:
        cols[f"rsi_xdn_{lv}"] = cross_down(rsi_a, float(lv))
    for lv in STOCH_XUP_LEVELS:
        cols[f"stoch_xup_{lv}"] = cross_up(stoch_a, float(lv))
    for lv in STOCH_XDN_LEVELS:
        cols[f"stoch_xdn_{lv}"] = cross_down(stoch_a, float(lv))
    if rsx_a is not None:
        for lv in RSX_XUP_LEVELS:
            cols[f"rsx_xup_{lv}"] = cross_up(rsx_a, float(lv))
        for lv in RSX_XDN_LEVELS:
            cols[f"rsx_xdn_{lv}"] = cross_down(rsx_a, float(lv))
    else:
        n = len(rsi_a)
        for lv in RSX_XUP_LEVELS:
            cols[f"rsx_xup_{lv}"] = np.zeros(n, dtype=float)
        for lv in RSX_XDN_LEVELS:
            cols[f"rsx_xdn_{lv}"] = np.zeros(n, dtype=float)
    return cols


def merge_cross_into_rows(rows: list[dict[str, float]], cross_cols: dict[str, np.ndarray]) -> None:
    """Mutate causal feature rows in place with cross event floats."""
    n = len(rows)
    for key, arr in cross_cols.items():
        for i in range(n):
            rows[i][key] = float(arr[i]) if i < len(arr) else 0.0


def compute_rsx_series(closes: np.ndarray, period: int = 14) -> np.ndarray | None:
    """Best-effort causal RSX via TA engine; None if unavailable."""
    try:
        import pandas as pd

        from trendalgo.ta.engine import compute
        from trendalgo.ta.signals import primary_series

        df = pd.DataFrame(
            {
                "open": closes,
                "high": closes,
                "low": closes,
                "close": closes,
                "volume": np.ones(len(closes)),
            }
        )
        out = compute("RSX", df, length=int(period))
        close = pd.Series(df["close"], dtype=float)
        series = primary_series("RSX", out, close)
        arr = np.nan_to_num(series.to_numpy(dtype=float), nan=50.0)
        return np.asarray(arr, dtype=float)
    except (TypeError, ValueError, KeyError, ImportError):
        return None
