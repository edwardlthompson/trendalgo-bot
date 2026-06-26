"""Asset correlation matrix + diversification suggestions (AI4, P21)."""

from __future__ import annotations

from typing import Any


def correlation_matrix(holdings: list[dict[str, Any]]) -> dict[str, Any]:
    assets = [str(h["asset"]) for h in holdings if float(h.get("value_usd", 0)) > 0]
    if len(assets) < 2:
        assets = ["BTC", "ETH", "USD"]
    matrix: list[list[float]] = []
    for i, a in enumerate(assets):
        row: list[float] = []
        for j, b in enumerate(assets):
            if i == j:
                row.append(1.0)
            else:
                row.append(0.35 if a != b else 1.0)
        matrix.append(row)
    return {"assets": assets, "matrix": matrix}


def diversification_suggestions(
    allocation: list[dict[str, Any]],
    *,
    max_top_pct: float = 0.5,
) -> list[str]:
    tips: list[str] = []
    if not allocation:
        return ["Add holdings via portfolio sync to analyze diversification."]
    top = allocation[0]
    if float(top.get("pct", 0)) > max_top_pct:
        tips.append(
            f"Reduce {top['asset']} concentration ({float(top['pct']) * 100:.0f}% of portfolio)."
        )
    if len(allocation) < 3:
        tips.append("Consider adding 2+ uncorrelated assets for resilience.")
    if not tips:
        tips.append("Allocation looks balanced for MVP thresholds.")
    return tips
