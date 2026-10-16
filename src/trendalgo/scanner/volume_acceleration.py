"""Volume Δ% — the LTS dashboard's "Vol Δ%" column, computed from 1h bars.

Mirrors upstream ``scanner/coin_enrichment.py::attach_volume_acceleration``:
the last 10 days of 1h base-asset volume (240 bars); the current window is the
last 24h; the baseline is up to 7 prior full 24h totals; the result is
``(current - baseline_avg) / baseline_avg * 100``.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any

from trendalgo.market.types import OhlcvPoint

LOOKBACK_BARS = 240  # 10 days of 1h candles
MIN_BARS = 48
MAX_BASELINE_DAYS = 7
HOURS_PER_DAY = 24

VOLUME_KEYS = (
    "volume_acceleration_pct",
    "volume_acceleration_window_days",
    "volume_recent_24h",
    "volume_baseline_24h",
)


def _finite_or_zero(value: float) -> float:
    return value if math.isfinite(value) else 0.0


def volume_acceleration_stats(volumes: Sequence[float]) -> dict[str, Any] | None:
    """Stats from oldest→newest 1h volumes, or ``None`` when history is too thin."""
    vols = [_finite_or_zero(float(v)) for v in volumes[-LOOKBACK_BARS:]]
    if len(vols) < MIN_BARS:
        return None
    current = vols[-HOURS_PER_DAY:]
    previous = vols[:-HOURS_PER_DAY]
    prior_days = min(MAX_BASELINE_DAYS, len(previous) // HOURS_PER_DAY)
    if prior_days <= 0:
        return None
    baseline_hours = previous[-(prior_days * HOURS_PER_DAY) :]
    totals = [
        sum(baseline_hours[start : start + HOURS_PER_DAY])
        for start in range(0, len(baseline_hours), HOURS_PER_DAY)
        if len(baseline_hours[start : start + HOURS_PER_DAY]) == HOURS_PER_DAY
    ]
    if not totals:
        return None
    recent = sum(current)
    baseline = sum(totals) / len(totals)
    if baseline <= 0:
        return None
    pct = (recent - baseline) / baseline * 100.0
    return {
        "volume_acceleration_pct": round(pct, 4),
        "volume_acceleration_window_days": len(totals),
        "volume_recent_24h": round(recent, 4),
        "volume_baseline_24h": round(baseline, 4),
    }


def apply_volume_acceleration(coin: dict[str, Any], bars_1h: Sequence[OhlcvPoint]) -> bool:
    """Set (or clear) the Vol Δ% keys on a coin row. Returns True when computed."""
    for key in VOLUME_KEYS:
        coin.pop(key, None)
    stats = volume_acceleration_stats([float(bar.volume) for bar in bars_1h])
    if stats is None:
        return False
    coin.update(stats)
    return True
