"""Causal structural regime lenses: ADX/DI, Efficiency Ratio, Choppiness."""

from __future__ import annotations

import numpy as np


def true_range(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray) -> np.ndarray:
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
    return tr


def adx_di(
    highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, *, period: int = 14
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Wilder-ish ADX, +DI, -DI (causal rolling)."""
    n = len(closes)
    adx = np.full(n, 20.0)
    plus_di = np.full(n, 25.0)
    minus_di = np.full(n, 25.0)
    if n < period + 1:
        return adx, plus_di, minus_di
    tr = true_range(highs, lows, closes)
    plus_dm = np.zeros(n)
    minus_dm = np.zeros(n)
    for i in range(1, n):
        up = highs[i] - highs[i - 1]
        down = lows[i - 1] - lows[i]
        plus_dm[i] = up if up > down and up > 0 else 0.0
        minus_dm[i] = down if down > up and down > 0 else 0.0
    atr = _wilder(tr, period)
    p_dm = _wilder(plus_dm, period)
    m_dm = _wilder(minus_dm, period)
    dx = np.zeros(n)
    for i in range(n):
        if atr[i] <= 1e-12:
            continue
        plus_di[i] = 100.0 * p_dm[i] / atr[i]
        minus_di[i] = 100.0 * m_dm[i] / atr[i]
        denom = plus_di[i] + minus_di[i]
        if denom > 1e-12:
            dx[i] = 100.0 * abs(plus_di[i] - minus_di[i]) / denom
    adx = _wilder(dx, period)
    return adx, plus_di, minus_di


def efficiency_ratio(closes: np.ndarray, *, period: int = 20) -> np.ndarray:
    n = len(closes)
    out = np.zeros(n)
    for i in range(n):
        if i < 1:
            continue
        start = max(0, i - period)
        net = abs(closes[i] - closes[start])
        path = float(np.sum(np.abs(np.diff(closes[start : i + 1]))))
        out[i] = (net / path) if path > 1e-12 else 0.0
    return out


def choppiness_index(
    highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, *, period: int = 14
) -> np.ndarray:
    n = len(closes)
    out = np.full(n, 50.0)
    tr = true_range(highs, lows, closes)
    log100 = np.log10(100.0)
    for i in range(n):
        if i < 1:
            continue
        w0 = max(0, i - period + 1)
        atr_sum = float(np.sum(tr[w0 : i + 1]))
        hh = float(np.max(highs[w0 : i + 1]))
        ll = float(np.min(lows[w0 : i + 1]))
        span = hh - ll
        if atr_sum <= 1e-12 or span <= 1e-12:
            continue
        out[i] = 100.0 * np.log10(atr_sum / span) / log100
    return out


def sma(closes: np.ndarray, period: int) -> np.ndarray:
    n = len(closes)
    out = np.zeros(n)
    for i in range(n):
        out[i] = float(np.mean(closes[max(0, i - period + 1) : i + 1]))
    return out


def _wilder(arr: np.ndarray, period: int) -> np.ndarray:
    n = len(arr)
    out = np.zeros(n)
    if n == 0:
        return out
    acc = 0.0
    for i in range(n):
        if i < period:
            acc = float(np.mean(arr[: i + 1])) if i else float(arr[0])
        else:
            acc = (acc * (period - 1) + arr[i]) / period
        out[i] = acc
    return out
