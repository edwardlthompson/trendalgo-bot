"""Stop distance and R:R to pivot targets (long framing)."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np

from trendalgo.analytics.classic_pivots import ATR_STOP_MULT


@dataclass(frozen=True)
class RiskMetrics:
    entry: float
    stop: float
    stop_distance_pct: float
    stop_distance_atr: float
    atr: float
    rr_to_r1: float | None
    rr_to_r2: float | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def atr_last(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14) -> float:
    n = len(closes)
    if n < 2:
        return 0.0
    trs: list[float] = []
    for i in range(1, n):
        h, low_v, prev_c = float(highs[i]), float(lows[i]), float(closes[i - 1])
        trs.append(max(h - low_v, abs(h - prev_c), abs(low_v - prev_c)))
    if not trs:
        return 0.0
    window = trs[-period:] if len(trs) >= period else trs
    return float(np.mean(window))


def compute_risk(
    entry: float,
    atr: float,
    *,
    r1: float | None,
    r2: float | None,
    stop_mult: float = ATR_STOP_MULT,
) -> RiskMetrics:
    """Long bias: stop = entry − ATR×mult; R:R to R1/R2."""
    entry_f = float(entry)
    atr_f = max(0.0, float(atr))
    stop = entry_f - stop_mult * atr_f if atr_f > 0 else entry_f * 0.99
    risk = max(entry_f - stop, 1e-12)
    stop_pct = 100.0 * risk / entry_f if entry_f else 0.0
    stop_atr = risk / atr_f if atr_f > 1e-12 else 0.0

    def _rr(target: float | None) -> float | None:
        if target is None or not np.isfinite(target):
            return None
        reward = float(target) - entry_f
        if reward <= 0:
            return None
        return round(reward / risk, 2)

    return RiskMetrics(
        entry=entry_f,
        stop=round(stop, 8),
        stop_distance_pct=round(stop_pct, 3),
        stop_distance_atr=round(stop_atr, 3),
        atr=round(atr_f, 8),
        rr_to_r1=_rr(r1),
        rr_to_r2=_rr(r2),
    )
