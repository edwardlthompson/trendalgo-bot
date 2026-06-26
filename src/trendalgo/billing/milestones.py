"""Profit milestone notifications — LS25-safe copy (M21)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

MILESTONE_THRESHOLDS = [100, 500, 1000, 5000]


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def detect_milestones(
    lifetime_profit_usd: float,
    already: list[float],
) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for threshold in MILESTONE_THRESHOLDS:
        if lifetime_profit_usd >= threshold and threshold not in already:
            hits.append(
                {
                    "milestone_usd": threshold,
                    "title": f"Profit milestone: ${threshold}",
                    "body": (
                        f"Your bot-attributed profits reached ${threshold}. "
                        "View your license statement — fees apply only on net-positive closed trades."
                    ),
                    "reached_at": _utc_now(),
                    "celebrate_pnl_not_fee": True,
                }
            )
    return hits
