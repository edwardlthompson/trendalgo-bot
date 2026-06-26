"""Portfolio event alerts — drop %, allocation breach (P10)."""

from __future__ import annotations

from typing import Any

from trendalgo.portfolio.db import PortfolioStore


def check_portfolio_alerts(
    store: PortfolioStore,
    account_id: int,
    overview: dict[str, Any],
    *,
    drop_threshold_pct: float = 0.05,
    max_allocation_pct: float = 0.7,
) -> list[str]:
    messages: list[str] = []
    daily_pct = float(overview.get("daily_pnl_pct", 0))
    if daily_pct <= -drop_threshold_pct:
        msg = f"Portfolio dropped {abs(daily_pct) * 100:.1f}% today"
        messages.append(msg)
        store.insert_notification("portfolio", "Portfolio drop alert", msg)
    allocation = overview.get("allocation", [])
    if allocation and float(allocation[0]["pct"]) > max_allocation_pct:
        asset = allocation[0]["asset"]
        msg = f"{asset} allocation {float(allocation[0]['pct']) * 100:.0f}% exceeds limit"
        messages.append(msg)
        store.insert_notification("portfolio", "Allocation breach", msg)
    return messages
