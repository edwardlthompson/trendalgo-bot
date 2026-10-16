"""LTS UniformityFilter port — score 0.0–1.0 for TrendAlgo scanner/strategies."""

from __future__ import annotations

import math
import statistics

from trendalgo.lts.adapter import OhlcvBar


def _trend_score_and_gain(closes: list[float], period: int) -> tuple[float, float]:
    """Port of UniformityFilter.calculate; returns (0–100 score, gain %)."""
    if len(closes) < period:
        return 0.0, 0.0
    prices = closes[-period:]
    base = prices[0]
    if base <= 0:
        return 0.0, 0.0
    cumulative = [((p - base) / base) * 100 for p in prices]
    total_gain = cumulative[-1]
    if total_gain <= 0:
        return 0.0, round(total_gain, 1)
    daily = total_gain / (period - 1)
    ideal = [i * daily for i in range(period)]
    total_dev = 0.0
    max_dev = 0.0
    for i in range(period):
        total_dev += abs(cumulative[i] - ideal[i])
        if i < period - 1:
            max_dev += total_gain
    normalized = (total_dev / max_dev) if max_dev > 0 else 0.0
    raw = 100 * (1 - math.sqrt(min(normalized, 1.0)))
    return min(100.0, max(0.0, round(raw, 1))), round(total_gain, 1)


def _ohlcv_composite(bars: list[OhlcvBar], period: int) -> float:
    """Port of UniformityFilter.calculate_from_ohlcv; returns 0–100."""
    sliced = bars[-period:]
    closes = [b.close for b in sliced]
    trend_score, _gain = _trend_score_and_gain(closes, period)
    body_ratios: list[float] = []
    bullish_flags: list[float] = []
    range_values: list[float] = []
    for bar in sliced:
        candle_range = max(1e-9, bar.high - bar.low)
        body = abs(bar.close - bar.open)
        body_ratios.append(body / candle_range)
        bullish_flags.append(1.0 if bar.close >= bar.open else 0.0)
        if bar.open > 0:
            range_values.append((candle_range / bar.open) * 100)
    body_score = statistics.mean(body_ratios) * 100 if body_ratios else 0.0
    bullish_score = statistics.mean(bullish_flags) * 100 if bullish_flags else 0.0
    if range_values:
        mean_range = statistics.mean(range_values)
        std_range = statistics.pstdev(range_values) if len(range_values) > 1 else 0.0
        range_stability = max(0.0, 100.0 - min(100.0, (std_range / max(0.1, mean_range)) * 100))
    else:
        range_stability = 0.0
    composite = (
        0.55 * trend_score + 0.20 * body_score + 0.15 * bullish_score + 0.10 * range_stability
    )
    return round(max(0.0, min(100.0, composite)), 1)


def uniformity_score(bars: list[OhlcvBar], lookback: int = 20) -> float:
    """Return 0.0–1.0 trend uniformity; 0.5 neutral when insufficient data."""
    if len(bars) < lookback or lookback < 2:
        return 0.5
    return round(_ohlcv_composite(bars, lookback) / 100.0, 4)
