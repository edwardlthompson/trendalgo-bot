"""Portfolio sync billing attribution by venue (S22)."""

from __future__ import annotations

from typing import Any


def attribution_by_venue(sync_results: dict[str, Any]) -> dict[str, float]:
    """Roll up synced portfolio USD totals per venue for billing reports."""
    totals: dict[str, float] = {}
    for result in sync_results.values():
        if not isinstance(result, dict) or result.get("skipped") or "total_usd" not in result:
            continue
        venue = str(result.get("venue") or "unknown")
        totals[venue] = round(totals.get(venue, 0.0) + float(result.get("total_usd", 0)), 2)
    return totals
