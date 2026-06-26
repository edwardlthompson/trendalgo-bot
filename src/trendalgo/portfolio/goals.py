"""Performance goal tracking (P22)."""

from __future__ import annotations

from typing import Any


def goal_progress(current_net_worth: float, goal: dict[str, Any]) -> dict[str, Any]:
    target = float(goal.get("target_net_worth_usd", 0))
    if target <= 0:
        progress_pct = 0.0
    else:
        progress_pct = min(1.0, current_net_worth / target)
    remaining = max(0.0, target - current_net_worth)
    return {
        **goal,
        "current_net_worth_usd": round(current_net_worth, 2),
        "progress_pct": round(progress_pct, 4),
        "remaining_usd": round(remaining, 2),
        "on_track": current_net_worth >= target,
    }
