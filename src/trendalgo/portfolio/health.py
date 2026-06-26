"""Portfolio health score (P11, U7)."""

from __future__ import annotations

from typing import Any

from trendalgo.portfolio.drawdown import max_drawdown


def health_score(
    allocation: list[dict[str, Any]],
    drawdown_pct: float,
    daily_pnl_pct: float,
) -> int:
    """0–100 score: diversification + low drawdown + positive momentum."""
    if not allocation:
        return 50
    top_pct = float(allocation[0]["pct"]) if allocation else 1.0
    diversity = max(0.0, 1.0 - top_pct) * 40
    dd_score = max(0.0, 1.0 - drawdown_pct * 5) * 30
    momentum = 15.0 if daily_pnl_pct >= 0 else 5.0
    return int(min(100, round(diversity + dd_score + momentum + 15)))
