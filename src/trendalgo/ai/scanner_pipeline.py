"""Scanner-to-strategy pipeline — qualified coins → templates (AI6)."""

from __future__ import annotations

from typing import Any


def pipeline_suggestions(opportunities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    suggestions: list[dict[str, Any]] = []
    for row in opportunities[:10]:
        uniformity = float(row.get("uniformity", 0))
        gain = float(row.get("gain_pct", 0))
        pair = str(row.get("pair", ""))
        if uniformity >= 0.65 and gain > 0.03:
            template_id = "strong-uptrend-scanner"
            entry = {"rsi_entry": 32, "lts_uniform_min": max(0.55, uniformity - 0.05)}
        elif gain > 0.08:
            template_id = "grid-trading"
            entry = {"grid_spacing_pct": 0.02}
        else:
            template_id = "smart-dca"
            entry = {"interval_hours": 24}
        suggestions.append(
            {
                "pair": pair,
                "uniformity": uniformity,
                "gain_pct": gain,
                "template_id": template_id,
                "suggested_params": entry,
                "disclaimer": "Backtest before deploy. Not financial advice.",
            }
        )
    return suggestions
