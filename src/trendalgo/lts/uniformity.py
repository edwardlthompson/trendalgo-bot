"""Uniformity score stub — parity with LTS scanner (S4.5)."""

from __future__ import annotations

from trendalgo.lts.adapter import OhlcvBar


def uniformity_score(bars: list[OhlcvBar], lookback: int = 20) -> float:
    """Return 0.0–1.0 trend uniformity; 0.5 neutral when insufficient data."""
    if len(bars) < lookback or lookback < 2:
        return 0.5
    window = bars[-lookback:]
    closes = [b.close for b in window]
    ups = sum(1 for i in range(1, len(closes)) if closes[i] >= closes[i - 1])
    return round(ups / (len(closes) - 1), 4)
