"""Causal TA series helpers for Secret Sauce feature bank (bars ≤ i)."""

from __future__ import annotations

import numpy as np


def rsi(closes: np.ndarray, period: int = 14) -> np.ndarray:
    n = len(closes)
    out = np.full(n, 50.0)
    if n < 2:
        return out
    delta = np.diff(closes, prepend=closes[0])
    gain = np.clip(delta, 0.0, None)
    loss = np.clip(-delta, 0.0, None)
    avg_g = avg_l = 0.0
    for i in range(1, n):
        if i < period:
            avg_g = float(np.mean(gain[1 : i + 1]))
            avg_l = float(np.mean(loss[1 : i + 1]))
        else:
            avg_g = (avg_g * (period - 1) + gain[i]) / period
            avg_l = (avg_l * (period - 1) + loss[i]) / period
        if avg_l <= 1e-12:
            out[i] = 100.0 if avg_g > 0 else 50.0
        else:
            out[i] = 100.0 - (100.0 / (1.0 + avg_g / avg_l))
    return out


def ema(arr: np.ndarray, period: int) -> np.ndarray:
    out = np.zeros(len(arr))
    if len(arr) == 0:
        return out
    alpha = 2.0 / (period + 1.0)
    out[0] = arr[0]
    for i in range(1, len(arr)):
        out[i] = alpha * arr[i] + (1.0 - alpha) * out[i - 1]
    return out


def macd_hist(closes: np.ndarray) -> np.ndarray:
    line = ema(closes, 12) - ema(closes, 26)
    return np.asarray(line - ema(line, 9), dtype=float)


def bb_pct_b(closes: np.ndarray, period: int = 20) -> np.ndarray:
    n = len(closes)
    out = np.full(n, 0.5)
    for i in range(n):
        w = closes[max(0, i - period + 1) : i + 1]
        mid = float(np.mean(w))
        std = float(np.std(w)) if len(w) > 1 else 0.0
        if std <= 1e-12:
            continue
        upper, lower = mid + 2.0 * std, mid - 2.0 * std
        out[i] = (closes[i] - lower) / (upper - lower) if upper != lower else 0.5
    return out


def atr_pct(
    highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14
) -> np.ndarray:
    n = len(closes)
    tr = np.zeros(n)
    for i in range(n):
        if i == 0:
            tr[i] = highs[i] - lows[i]
        else:
            tr[i] = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1]),
            )
    out = np.zeros(n)
    atr = 0.0
    for i in range(n):
        atr = float(np.mean(tr[: i + 1])) if i < period else (atr * (period - 1) + tr[i]) / period
        out[i] = (atr / closes[i]) if closes[i] else 0.0
    return out


def stoch_k(
    highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14
) -> np.ndarray:
    n = len(closes)
    out = np.full(n, 50.0)
    for i in range(n):
        hi = float(np.max(highs[max(0, i - period + 1) : i + 1]))
        lo = float(np.min(lows[max(0, i - period + 1) : i + 1]))
        out[i] = 50.0 if hi <= lo else 100.0 * (closes[i] - lo) / (hi - lo)
    return out
