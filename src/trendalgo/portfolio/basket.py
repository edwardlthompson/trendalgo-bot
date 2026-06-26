"""Portfolio basket allocation for bot weights (T26)."""

from __future__ import annotations

from typing import Any


def normalize_weights(weights: dict[str, float]) -> dict[str, float]:
    total = sum(weights.values())
    if total <= 0:
        return weights
    return {k: round(v / total, 4) for k, v in weights.items()}


def apply_basket_to_bots(
    bots: list[dict[str, Any]],
    weights: dict[str, float],
    portfolio_total_usd: float,
) -> list[dict[str, Any]]:
    normalized = normalize_weights(weights)
    result: list[dict[str, Any]] = []
    for bot in bots:
        key = str(bot["id"])
        w = normalized.get(key, 0.0)
        result.append(
            {
                "bot_id": int(bot["id"]),
                "label": bot["label"],
                "weight_pct": w,
                "suggested_equity_usd": round(portfolio_total_usd * w, 2),
                "current_equity_usd": float(bot.get("equity_usd", 0)),
            }
        )
    return result
