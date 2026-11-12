"""Beta-weighted exposure cap (FEAT-04).

Correlated longs must not stack into one directional bet: cap Σ(|notional| × |β|)
against equity × max_beta_exposure.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class PositionBeta:
    symbol: str
    notional_usd: float
    beta: float


def beta_weighted_exposure(positions: Iterable[PositionBeta]) -> float:
    """Aggregate |notional| × |beta| (long/short both consume budget)."""
    total = 0.0
    for pos in positions:
        total += abs(float(pos.notional_usd)) * abs(float(pos.beta))
    return total


def beta_exposure_error(
    positions: Iterable[PositionBeta],
    *,
    equity_usd: float,
    max_beta_exposure: float,
) -> str | None:
    """None when within cap; otherwise a rejection reason."""
    if equity_usd < 0 or not math.isfinite(equity_usd):
        return "beta exposure rejected: equity must be a finite non-negative number"
    if max_beta_exposure < 0 or not math.isfinite(max_beta_exposure):
        return "beta exposure rejected: max_beta_exposure must be finite and >= 0"
    limit = float(equity_usd) * float(max_beta_exposure)
    used = beta_weighted_exposure(positions)
    if used > limit:
        return (
            f"beta exposure rejected: weighted {used:.2f} exceeds {limit:.2f} "
            f"(equity {equity_usd:.2f} x max beta exposure {max_beta_exposure:.2f})"
        )
    return None
