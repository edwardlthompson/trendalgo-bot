"""Causal Fib / swing-structure features (past bars only)."""

from __future__ import annotations

import numpy as np

STRUCTURE_KEYS = (
    "fib_dist_382",
    "fib_dist_500",
    "fib_dist_618",
    "fib_touch_618",
    "swing_up_span",
    "ema_xup_20_50",
    "ema_xdn_20_50",
    "mom_10",
    "roc_10",
    "slope_10",
)


def merge_structure_into_rows(
    closes: np.ndarray,
    highs: np.ndarray,
    lows: np.ndarray,
    rows: list[dict[str, float]],
) -> None:
    """Fib distances from last confirmed swing + EMA cross + MOM/ROC/slope."""
    n = len(rows)
    if n == 0 or len(closes) != n:
        return
    ema20 = _ema(closes, 20)
    ema50 = _ema(closes, 50)
    for i, row in enumerate(rows):
        swing_lo, swing_hi = _swing_window(lows, highs, i)
        span = float(swing_hi - swing_lo)
        if span <= 1e-12 or not np.isfinite(span):
            row["fib_dist_382"] = 0.0
            row["fib_dist_500"] = 0.0
            row["fib_dist_618"] = 0.0
            row["fib_touch_618"] = 0.0
            row["swing_up_span"] = 0.0
        else:
            c = float(closes[i])
            lvl382 = swing_hi - 0.382 * span
            lvl500 = swing_hi - 0.500 * span
            lvl618 = swing_hi - 0.618 * span
            row["fib_dist_382"] = (c - lvl382) / span
            row["fib_dist_500"] = (c - lvl500) / span
            row["fib_dist_618"] = (c - lvl618) / span
            row["fib_touch_618"] = 1.0 if abs(c - lvl618) / span <= 0.02 else 0.0
            row["swing_up_span"] = span / c if c else 0.0
        e20, e50 = float(ema20[i]), float(ema50[i])
        pe20 = float(ema20[i - 1]) if i else e20
        pe50 = float(ema50[i - 1]) if i else e50
        row["ema_xup_20_50"] = 1.0 if pe20 <= pe50 and e20 > e50 else 0.0
        row["ema_xdn_20_50"] = 1.0 if pe20 >= pe50 and e20 < e50 else 0.0
        look = 10
        past = closes[max(0, i - look)]
        row["mom_10"] = float(closes[i] - past)
        row["roc_10"] = float((closes[i] / past - 1.0) if past else 0.0)
        row["slope_10"] = float((closes[i] - past) / look if look else 0.0)


def _swing_window(lows: np.ndarray, highs: np.ndarray, i: int) -> tuple[float, float]:
    # Confirmed past swing: lookback 20 bars ending at i (no future).
    start = max(0, i - 19)
    return float(np.min(lows[start : i + 1])), float(np.max(highs[start : i + 1]))


def _ema(series: np.ndarray, period: int) -> np.ndarray:
    out = np.zeros(len(series), dtype=float)
    if len(series) == 0:
        return out
    alpha = 2.0 / (period + 1.0)
    out[0] = float(series[0])
    for i in range(1, len(series)):
        out[i] = alpha * float(series[i]) + (1.0 - alpha) * out[i - 1]
    return out
