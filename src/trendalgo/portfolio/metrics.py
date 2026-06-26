"""Portfolio P/L and period metrics (P6, P7)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any


@dataclass(frozen=True)
class PlBreakdown:
    realized_usd: float
    unrealized_usd: float
    total_usd: float


@dataclass(frozen=True)
class PeriodPl:
    label: str
    pnl_usd: float
    pnl_pct: float


def _parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def daily_pnl_from_curve(curve: list[dict[str, Any]]) -> tuple[float, float]:
    """Return (daily_pnl_usd, daily_pnl_pct) from last two equity points."""
    if len(curve) < 2:
        if curve:
            return 0.0, 0.0
        return 0.0, 0.0
    prev = float(curve[-2]["total_usd"])
    last = float(curve[-1]["total_usd"])
    pnl = last - prev
    pct = pnl / prev if prev else 0.0
    return round(pnl, 2), round(pct, 4)


def pl_breakdown(holdings: list[dict[str, Any]]) -> PlBreakdown:
    unrealized = 0.0
    for h in holdings:
        value = float(h.get("value_usd", 0))
        cost = float(h.get("cost_basis_usd", 0))
        unrealized += value - cost
    realized = 0.0
    total = realized + unrealized
    return PlBreakdown(
        realized_usd=round(realized, 2),
        unrealized_usd=round(unrealized, 2),
        total_usd=round(total, 2),
    )


def allocation_rows(holdings: list[dict[str, Any]], total_usd: float) -> list[dict[str, Any]]:
    if total_usd <= 0:
        return []
    rows: list[dict[str, Any]] = []
    for h in holdings:
        value = float(h["value_usd"])
        rows.append(
            {
                "asset": h["asset"],
                "value_usd": value,
                "pct": round(value / total_usd, 4),
            }
        )
    return sorted(rows, key=lambda r: r["value_usd"], reverse=True)


def period_comparison(curve: list[dict[str, Any]]) -> list[PeriodPl]:
    if not curve:
        return []
    now = _parse_ts(str(curve[-1]["captured_at"]))
    periods = [
        ("daily", now - timedelta(days=1)),
        ("weekly", now - timedelta(days=7)),
        ("monthly", now - timedelta(days=30)),
    ]
    last_total = float(curve[-1]["total_usd"])
    result: list[PeriodPl] = []
    for label, cutoff in periods:
        baseline = last_total
        for point in curve:
            ts = _parse_ts(str(point["captured_at"]))
            if ts <= cutoff:
                baseline = float(point["total_usd"])
        pnl = last_total - baseline
        pct = pnl / baseline if baseline else 0.0
        result.append(PeriodPl(label=label, pnl_usd=round(pnl, 2), pnl_pct=round(pct, 4)))
    return result


def enrich_holdings(holdings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for h in holdings:
        value = float(h["value_usd"])
        cost = float(h.get("cost_basis_usd", 0))
        qty = float(h["quantity"])
        price = float(h["price_usd"])
        unrealized = value - cost
        pct_change = (price / (cost / qty) - 1) if cost and qty else 0.0
        enriched.append(
            {
                **h,
                "unrealized_pnl_usd": round(unrealized, 2),
                "pct_change": round(pct_change, 4),
            }
        )
    return enriched
