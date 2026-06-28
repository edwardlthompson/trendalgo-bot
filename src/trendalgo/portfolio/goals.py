"""Performance goal tracking (P22)."""

from __future__ import annotations

from typing import Any


def _comparison_pct(comparisons: list[dict[str, Any]], label: str) -> float:
    for row in comparisons:
        if row.get("label") == label:
            return float(row.get("pnl_pct", 0))
    return 0.0


def goal_progress(
    current_net_worth: float,
    goal: dict[str, Any],
    *,
    max_drawdown_pct: float = 0.0,
    comparisons: list[dict[str, Any]] | None = None,
    alpha_pct: float = 0.0,
) -> dict[str, Any]:
    comparisons = comparisons or []
    mom_return_pct = _comparison_pct(comparisons, "mom")
    yoy_return_pct = _comparison_pct(comparisons, "yoy")
    goal_type = str(goal.get("goal_type") or "portfolio_growth")
    target_usd = float(goal.get("target_net_worth_usd", 0))
    target_pct = float(goal.get("target_return_pct") or 0)
    horizon_months = int(goal.get("horizon_months") or 12)

    progress_pct = 0.0
    if goal_type == "portfolio_growth":
        progress_pct = min(1.0, current_net_worth / target_usd) if target_usd > 0 else 0.0
    elif goal_type == "annual_return":
        current = yoy_return_pct if yoy_return_pct else mom_return_pct * 12
        progress_pct = min(1.0, current / target_pct) if target_pct > 0 else 0.0
    elif goal_type == "monthly_return":
        progress_pct = min(1.0, mom_return_pct / target_pct) if target_pct > 0 else 0.0
    elif goal_type == "capital_preservation":
        if target_pct <= 0:
            progress_pct = 1.0 if max_drawdown_pct <= 0 else 0.0
        elif max_drawdown_pct <= target_pct:
            progress_pct = 1.0
        else:
            progress_pct = max(0.0, 1.0 - (max_drawdown_pct - target_pct) / target_pct)
    elif goal_type == "beat_btc":
        if target_pct > 0:
            progress_pct = min(1.0, max(0.0, alpha_pct) / target_pct)
        else:
            progress_pct = 1.0 if alpha_pct > 0 else 0.0
    elif goal_type == "income":
        progress_pct = min(1.0, current_net_worth / target_usd) if target_usd > 0 else 0.0

    remaining = max(0.0, target_usd - current_net_worth)
    return {
        **goal,
        "goal_type": goal_type,
        "horizon_months": horizon_months,
        "target_return_pct": round(target_pct, 4),
        "current_net_worth_usd": round(current_net_worth, 2),
        "progress_pct": round(progress_pct, 4),
        "remaining_usd": round(remaining, 2),
        "on_track": progress_pct >= 1.0,
        "mom_return_pct": round(mom_return_pct, 4),
        "yoy_return_pct": round(yoy_return_pct, 4),
        "alpha_pct": round(alpha_pct, 4),
    }
