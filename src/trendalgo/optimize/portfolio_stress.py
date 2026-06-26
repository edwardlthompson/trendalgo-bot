"""Portfolio-level Monte Carlo stress (AI3)."""

from __future__ import annotations

import random
from typing import Any


def portfolio_monte_carlo(
    net_worth_usd: float,
    daily_returns: list[float],
    *,
    simulations: int = 100,
    horizon_days: int = 30,
    seed: int = 7,
) -> dict[str, Any]:
    if not daily_returns:
        daily_returns = [0.001, -0.002, 0.003, 0.0, 0.0015]
    rng = random.Random(seed)
    finals: list[float] = []
    for _ in range(simulations):
        value = net_worth_usd
        for _d in range(horizon_days):
            value *= 1 + rng.choice(daily_returns)
        finals.append(value)
    finals.sort()
    n = len(finals)
    return {
        "horizon_days": horizon_days,
        "simulations": simulations,
        "start_usd": net_worth_usd,
        "p5_usd": round(finals[int(n * 0.05)], 2),
        "p50_usd": round(finals[int(n * 0.5)], 2),
        "p95_usd": round(finals[int(n * 0.95)], 2),
        "scenarios": [
            {"label": "mild_drawdown", "end_usd": round(net_worth_usd * 0.92, 2)},
            {"label": "base", "end_usd": round(net_worth_usd * 1.02, 2)},
            {"label": "stress", "end_usd": round(net_worth_usd * 0.85, 2)},
        ],
    }
