"""Monte Carlo robustness — trade shuffle + confidence intervals (T17)."""

from __future__ import annotations

import random
from typing import Any


def monte_carlo_trade_shuffle(
    profits: list[float],
    *,
    simulations: int = 200,
    seed: int = 42,
) -> dict[str, Any]:
    if not profits:
        profits = [12.0, -8.0, 21.0, -2.0, 9.0]
    rng = random.Random(seed)
    totals: list[float] = []
    for _ in range(simulations):
        shuffled = profits.copy()
        rng.shuffle(shuffled)
        totals.append(sum(shuffled))
    totals.sort()
    n = len(totals)
    p5 = totals[int(n * 0.05)]
    p50 = totals[int(n * 0.5)]
    p95 = totals[int(n * 0.95)]
    return {
        "simulations": simulations,
        "p5": round(p5, 2),
        "p50": round(p50, 2),
        "p95": round(p95, 2),
        "mean": round(sum(totals) / n, 2),
    }
