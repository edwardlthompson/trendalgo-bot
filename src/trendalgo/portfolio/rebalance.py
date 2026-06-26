"""Portfolio rebalancing suggestions (P15)."""

from __future__ import annotations

from typing import Any


def rebalance_suggestions(
    allocation: list[dict[str, Any]],
    targets: list[dict[str, Any]],
    total_usd: float,
) -> list[dict[str, Any]]:
    if total_usd <= 0:
        return []
    current = {str(a["asset"]): float(a["pct"]) for a in allocation}
    target_map = {str(t["asset"]): float(t["target_pct"]) for t in targets}
    all_assets = set(current) | set(target_map)
    suggestions: list[dict[str, Any]] = []
    for asset in sorted(all_assets):
        cur_pct = current.get(asset, 0.0)
        tgt_pct = target_map.get(asset, 0.0)
        delta_pct = tgt_pct - cur_pct
        if abs(delta_pct) < 0.01:
            continue
        delta_usd = round(delta_pct * total_usd, 2)
        action = "buy" if delta_usd > 0 else "sell"
        suggestions.append(
            {
                "asset": asset,
                "current_pct": round(cur_pct, 4),
                "target_pct": round(tgt_pct, 4),
                "delta_pct": round(delta_pct, 4),
                "delta_usd": delta_usd,
                "action": action,
                "manual_only": True,
            }
        )
    return sorted(suggestions, key=lambda s: abs(s["delta_usd"]), reverse=True)
