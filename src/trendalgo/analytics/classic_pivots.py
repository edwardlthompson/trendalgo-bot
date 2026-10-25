"""Classic floor-trader pivots (PP, S1–S3, R1–R3) — prior period only (causal)."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np

LEVEL_NAMES = ("R3", "R2", "R1", "PP", "S1", "S2", "S3")
ATR_STOP_MULT = 1.5


@dataclass(frozen=True)
class PivotLevel:
    name: str
    price: float
    strength: float  # 0–100


@dataclass(frozen=True)
class PivotSet:
    levels: tuple[PivotLevel, ...]
    prior_high: float
    prior_low: float
    prior_close: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "levels": [asdict(level) for level in self.levels],
            "prior_high": self.prior_high,
            "prior_low": self.prior_low,
            "prior_close": self.prior_close,
        }

    def price_map(self) -> dict[str, float]:
        return {level.name: level.price for level in self.levels}


def classic_levels(high: float, low: float, close: float) -> dict[str, float]:
    """Floor-trader formulas from one completed period H/L/C."""
    h, low_v, c = float(high), float(low), float(close)
    pp = (h + low_v + c) / 3.0
    r1 = 2.0 * pp - low_v
    s1 = 2.0 * pp - h
    r2 = pp + (h - low_v)
    s2 = pp - (h - low_v)
    r3 = h + 2.0 * (pp - low_v)
    s3 = low_v - 2.0 * (h - pp)
    return {"PP": pp, "R1": r1, "R2": r2, "R3": r3, "S1": s1, "S2": s2, "S3": s3}


def prior_period_hlc(
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    *,
    period_bars: int = 24,
) -> tuple[float, float, float] | None:
    """Prior completed window ending before the last bar (no same-bar leak)."""
    n = len(closes)
    if n < period_bars + 1:
        return None
    end = n - 1  # exclusive of current bar
    start = max(0, end - period_bars)
    if end - start < 2:
        return None
    window_h = highs[start:end]
    window_l = lows[start:end]
    prior_c = float(closes[end - 1])
    return float(np.nanmax(window_h)), float(np.nanmin(window_l)), prior_c


def level_strength(
    price: float,
    closes: np.ndarray,
    highs: np.ndarray,
    lows: np.ndarray,
    *,
    lookback: int = 48,
    tol_pct: float = 0.002,
) -> float:
    """0–100 from touches + rejection rate in recent bars."""
    n = len(closes)
    if n < 3 or not np.isfinite(price) or price <= 0:
        return 0.0
    start = max(0, n - lookback)
    touches = 0
    rejections = 0
    for i in range(start, n):
        hi, lo, c = float(highs[i]), float(lows[i]), float(closes[i])
        if lo <= price <= hi or abs(c - price) / price <= tol_pct:
            touches += 1
            if i > 0:
                prev = float(closes[i - 1])
                if (prev < price and c < price) or (prev > price and c > price):
                    rejections += 1
    if touches <= 0:
        return 10.0
    rate = rejections / touches
    return float(max(0.0, min(100.0, 20.0 + 15.0 * touches + 40.0 * rate)))


def compute_pivot_set(
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    *,
    period_bars: int = 24,
) -> PivotSet | None:
    hlc = prior_period_hlc(highs, lows, closes, period_bars=period_bars)
    if hlc is None:
        return None
    h, low_v, c = hlc
    raw = classic_levels(h, low_v, c)
    levels = tuple(
        PivotLevel(
            name=name,
            price=raw[name],
            strength=level_strength(raw[name], closes, highs, lows),
        )
        for name in LEVEL_NAMES
    )
    return PivotSet(levels=levels, prior_high=h, prior_low=low_v, prior_close=c)
