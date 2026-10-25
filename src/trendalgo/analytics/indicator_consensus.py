"""Traditional multi-indicator consensus (−2…+2 each → Buy/Sell/Neutral)."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True)
class ConsensusResult:
    signal: str  # Buy | Sell | Neutral
    score: float  # average −2…+2
    confidence: float  # 0–100
    votes: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _rsi(closes: np.ndarray, period: int = 14) -> float:
    n = len(closes)
    if n <= period:
        return 50.0
    deltas = np.diff(closes[-(period + 1) :])
    gains = np.clip(deltas, 0, None)
    losses = np.clip(-deltas, 0, None)
    avg_g = float(np.mean(gains)) if len(gains) else 0.0
    avg_l = float(np.mean(losses)) if len(losses) else 0.0
    if avg_l <= 1e-12:
        return 100.0 if avg_g > 0 else 50.0
    rs = avg_g / avg_l
    return 100.0 - (100.0 / (1.0 + rs))


def _sma(closes: np.ndarray, period: int) -> float | None:
    if len(closes) < period:
        return None
    return float(np.mean(closes[-period:]))


def _macd_hist(closes: np.ndarray) -> float:
    if len(closes) < 35:
        return 0.0
    ema12 = _ema_last(closes, 12)
    ema26 = _ema_last(closes, 26)
    macd = ema12 - ema26
    # Approximate signal as EMA of last macd-like diffs via price EMA gap slope
    prev = _ema_last(closes[:-1], 12) - _ema_last(closes[:-1], 26)
    return float(macd - prev)


def _ema_last(closes: np.ndarray, period: int) -> float:
    if len(closes) == 0:
        return 0.0
    alpha = 2.0 / (period + 1.0)
    value = float(closes[0])
    for price in closes[1:]:
        value = alpha * float(price) + (1.0 - alpha) * value
    return value


def _stoch_k(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14) -> float:
    if len(closes) < period:
        return 50.0
    hi = float(np.max(highs[-period:]))
    lo = float(np.min(lows[-period:]))
    if hi - lo <= 1e-12:
        return 50.0
    return 100.0 * (float(closes[-1]) - lo) / (hi - lo)


def _cci(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 20) -> float:
    if len(closes) < period:
        return 0.0
    tp = (highs[-period:] + lows[-period:] + closes[-period:]) / 3.0
    mean = float(np.mean(tp))
    mad = float(np.mean(np.abs(tp - mean)))
    if mad <= 1e-12:
        return 0.0
    return (float(tp[-1]) - mean) / (0.015 * mad)


def _clamp_vote(raw: float) -> float:
    return float(max(-2.0, min(2.0, raw)))


def compute_consensus(
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
) -> ConsensusResult:
    """Fixed traditional set → average score and Buy/Sell/Neutral."""
    if len(closes) < 30:
        return ConsensusResult("Neutral", 0.0, 0.0, {})

    rsi = _rsi(closes)
    # RSI: oversold bullish, overbought bearish
    rsi_v = _clamp_vote((50.0 - rsi) / 20.0)

    hist = _macd_hist(closes)
    macd_v = _clamp_vote(hist / (abs(float(closes[-1])) * 0.001 + 1e-9))

    stoch = _stoch_k(highs, lows, closes)
    stoch_v = _clamp_vote((50.0 - stoch) / 25.0)

    cci = _cci(highs, lows, closes)
    cci_v = _clamp_vote(cci / 100.0)

    sma50 = _sma(closes, 50)
    sma200 = _sma(closes, min(200, len(closes)))
    price = float(closes[-1])
    trend_v = 0.0
    if sma50 is not None:
        trend_v += 1.0 if price >= sma50 else -1.0
    if sma200 is not None and sma50 is not None:
        trend_v += 1.0 if sma50 >= sma200 else -1.0
    trend_v = _clamp_vote(trend_v)

    votes = {
        "rsi": round(rsi_v, 3),
        "macd": round(macd_v, 3),
        "stoch": round(stoch_v, 3),
        "cci": round(cci_v, 3),
        "trend": round(trend_v, 3),
    }
    score = float(sum(votes.values()) / len(votes))
    if score >= 0.35:
        signal = "Buy"
    elif score <= -0.35:
        signal = "Sell"
    else:
        signal = "Neutral"
    confidence = float(min(100.0, abs(score) / 2.0 * 100.0))
    return ConsensusResult(signal, round(score, 3), round(confidence, 1), votes)
