"""Side-by-side backtest comparison (T11, T32)."""

from __future__ import annotations

from typing import Any


def compare_runs(runs: list[dict[str, Any]]) -> dict[str, Any]:
    if not runs:
        return {"runs": [], "winner": None}
    ranked = sorted(
        runs,
        key=lambda r: float(r.get("metrics", {}).get("sharpe_ratio", 0) or 0),
        reverse=True,
    )
    return {
        "runs": ranked,
        "winner": ranked[0].get("id"),
        "count": len(ranked),
    }
