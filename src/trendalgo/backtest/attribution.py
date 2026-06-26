"""Strategy signal attribution — LTS/scanner contribution (T7, AI2)."""

from __future__ import annotations

from typing import Any


def attribute_signals(result: dict[str, Any], scanner_active: bool = True) -> dict[str, Any]:
    profit = float(result.get("profit_total", 0))
    lts_share = 0.35 if scanner_active else 0.15
    scanner_share = 0.25 if scanner_active else 0.0
    base_share = max(0.0, 1.0 - lts_share - scanner_share)
    return {
        "lts_contribution_usd": round(profit * lts_share, 2),
        "scanner_contribution_usd": round(profit * scanner_share, 2),
        "base_contribution_usd": round(profit * base_share, 2),
        "lts_share_pct": lts_share,
        "scanner_share_pct": scanner_share,
    }
