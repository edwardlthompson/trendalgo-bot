"""Causal volatility regime lenses: ATR/BB percentiles, squeeze flag."""

from __future__ import annotations

import numpy as np

from trendalgo.backtest.secret_sauce_lab.regime_structural import true_range
from trendalgo.backtest.secret_sauce_ta_series import atr_pct


def atr_percentile(
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    *,
    period: int = 14,
    lookback: int = 50,
) -> np.ndarray:
    atr = atr_pct(highs, lows, closes, period)
    n = len(closes)
    out = np.full(n, 0.5)
    for i in range(n):
        w0 = max(0, i - lookback + 1)
        window = atr[w0 : i + 1]
        if len(window) < 2:
            continue
        out[i] = float(np.mean(window <= atr[i]))
    return out


def bb_width_percentile(closes: np.ndarray, *, period: int = 20, lookback: int = 50) -> np.ndarray:
    n = len(closes)
    width = np.zeros(n)
    for i in range(n):
        w = closes[max(0, i - period + 1) : i + 1]
        mid = float(np.mean(w))
        std = float(np.std(w)) if len(w) > 1 else 0.0
        width[i] = (4.0 * std / mid) if mid > 1e-12 else 0.0
    out = np.full(n, 0.5)
    for i in range(n):
        w0 = max(0, i - lookback + 1)
        window = width[w0 : i + 1]
        if len(window) < 2:
            continue
        out[i] = float(np.mean(window <= width[i]))
    return out


def squeeze_flag(
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    *,
    period: int = 20,
    bb_mult: float = 2.0,
    kc_mult: float = 1.5,
) -> np.ndarray:
    """True when Bollinger band is inside Keltner channel (causal)."""
    n = len(closes)
    out = np.zeros(n, dtype=bool)
    tr = true_range(highs, lows, closes)
    for i in range(n):
        w0 = max(0, i - period + 1)
        mid = float(np.mean(closes[w0 : i + 1]))
        std = float(np.std(closes[w0 : i + 1])) if i > w0 else 0.0
        atr = float(np.mean(tr[w0 : i + 1]))
        bb_hi, bb_lo = mid + bb_mult * std, mid - bb_mult * std
        kc_hi, kc_lo = mid + kc_mult * atr, mid - kc_mult * atr
        out[i] = bb_hi <= kc_hi and bb_lo >= kc_lo
    return out
