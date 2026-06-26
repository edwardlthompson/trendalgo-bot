"""Dynamic ATR / volatility position sizing (T14)."""

from __future__ import annotations


def atr_stake_size(
    wallet_usd: float,
    atr_pct: float,
    *,
    risk_pct: float = 0.01,
    min_stake: float = 10.0,
    max_stake: float = 500.0,
) -> float:
    if atr_pct <= 0:
        return min_stake
    raw = wallet_usd * risk_pct / atr_pct
    return round(max(min_stake, min(max_stake, raw)), 2)
