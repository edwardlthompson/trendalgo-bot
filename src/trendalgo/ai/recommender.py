"""AI strategy recommender — scanner + risk profile (AI5)."""

from __future__ import annotations

from typing import Any

from trendalgo.templates.registry import list_templates


def _risk_profile_score(risk: dict[str, Any]) -> str:
    dd = float(risk.get("drawdown_pct", 0))
    if risk.get("circuit_breaker_active"):
        return "defensive"
    if dd > 0.08:
        return "cautious"
    if float(risk.get("equity_usd", 0)) < 500:
        return "small_account"
    return "balanced"


def recommend_strategies(
    opportunities: list[dict[str, Any]],
    risk: dict[str, Any],
    *,
    top_scanner_uniformity: float = 0.0,
) -> list[dict[str, Any]]:
    profile = _risk_profile_score(risk)
    has_scanner_signal = bool(opportunities) or top_scanner_uniformity >= 0.55
    ranked: list[dict[str, Any]] = []

    for tpl in list_templates():
        score = 40.0
        reasons: list[str] = []
        if tpl.kind == "scanner" and has_scanner_signal:
            score += 35
            reasons.append("LTS scanner opportunities active")
        if tpl.kind == "dca" and profile in ("balanced", "small_account"):
            score += 25
            reasons.append("DCA suits steady accumulation")
        if tpl.kind == "grid" and profile == "balanced":
            score += 20
            reasons.append("Grid for range-bound pairs")
        if tpl.kind == "multi-tf" and profile == "cautious":
            score += 15
            reasons.append("Multi-TF adds confirmation filters")
        if profile == "defensive" and tpl.kind in ("dca", "multi-tf"):
            score += 10
            reasons.append("Lower aggression profile")
        ranked.append(
            {
                "strategy_id": tpl.id,
                "kind": tpl.kind,
                "description": tpl.description,
                "score": round(score, 1),
                "reasons": reasons,
                "requires_backtest": True,
                "user_confirms_params": True,
            }
        )

    ranked.sort(key=lambda r: r["score"], reverse=True)
    return ranked
