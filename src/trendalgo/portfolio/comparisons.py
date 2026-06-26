"""YoY / MoM portfolio comparisons (P16)."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any


def _parse_date(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def yoy_mom_comparison(
    daily_aggregates: list[dict[str, Any]],
    equity_curve: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not equity_curve:
        return []

    last_total = float(equity_curve[-1]["total_usd"])
    last_ts = _parse_date(str(equity_curve[-1]["captured_at"]))
    now = last_ts

    def find_baseline(days: int) -> float:
        cutoff = now - timedelta(days=days)
        baseline = last_total
        for point in equity_curve:
            ts = _parse_date(str(point["captured_at"]))
            if ts <= cutoff:
                baseline = float(point["total_usd"])
        return baseline

    mom_baseline = find_baseline(30)
    yoy_baseline = find_baseline(365)

    comparisons = [
        {
            "label": "mom",
            "title": "Month over month",
            "pnl_usd": round(last_total - mom_baseline, 2),
            "pnl_pct": round((last_total - mom_baseline) / mom_baseline, 4)
            if mom_baseline
            else 0.0,
            "baseline_usd": round(mom_baseline, 2),
            "current_usd": round(last_total, 2),
        },
        {
            "label": "yoy",
            "title": "Year over year",
            "pnl_usd": round(last_total - yoy_baseline, 2),
            "pnl_pct": round((last_total - yoy_baseline) / yoy_baseline, 4)
            if yoy_baseline
            else 0.0,
            "baseline_usd": round(yoy_baseline, 2),
            "current_usd": round(last_total, 2),
        },
    ]

    if daily_aggregates:
        month_start = (now - timedelta(days=30)).strftime("%Y-%m-%d")
        month_pnl = sum(
            float(d.get("daily_pnl_usd", 0))
            for d in daily_aggregates
            if str(d["date"]) >= month_start
        )
        comparisons.append(
            {
                "label": "mtd",
                "title": "Month to date (daily sum)",
                "pnl_usd": round(month_pnl, 2),
                "pnl_pct": round(month_pnl / mom_baseline, 4) if mom_baseline else 0.0,
                "baseline_usd": round(mom_baseline, 2),
                "current_usd": round(last_total, 2),
            }
        )

    return comparisons
