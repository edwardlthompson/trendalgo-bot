"""Funding rate & perpetual display + profit calculation hooks (P13, T26)."""

from __future__ import annotations

import os
from typing import Any


def _dry_funding_rows() -> list[dict[str, Any]]:
    return [
        {
            "exchange": "binanceus",
            "pair": "BTC/USDT:USDT",
            "funding_rate_pct": 0.01,
            "next_funding_hours": 8,
            "mark_price_usd": 50000.0,
        },
        {
            "exchange": "binanceus",
            "pair": "ETH/USDT:USDT",
            "funding_rate_pct": 0.008,
            "next_funding_hours": 8,
            "mark_price_usd": 3000.0,
        },
        {
            "exchange": "kraken",
            "pair": "BTC/USD:USD",
            "funding_rate_pct": -0.002,
            "next_funding_hours": 4,
            "mark_price_usd": 49950.0,
        },
    ]


def fetch_funding_rates(exchange: str | None = None, *, dry_run: bool = True) -> dict[str, Any]:
    """Return perpetual funding snapshots (dry-run unless futures API keys set)."""
    live = not dry_run and os.environ.get("BINANCEUS_API_KEY") and exchange == "binanceus"
    rows = _dry_funding_rows()
    if exchange:
        rows = [r for r in rows if r["exchange"] == exchange]
    return {
        "rows": rows,
        "live": live,
        "display_only": True,
        "profit_hooks_enabled": True,
    }


def funding_profit_estimate(
    position_usd: float,
    funding_rate_pct: float,
    *,
    hours: int = 8,
    periods_per_day: int = 3,
) -> dict[str, float | str]:
    """Estimate funding PnL for a perpetual position (informational)."""
    if position_usd < 0:
        raise ValueError("position_usd must be non-negative")
    rate = funding_rate_pct / 100.0
    per_period = position_usd * rate
    daily = per_period * periods_per_day
    return {
        "position_usd": round(position_usd, 2),
        "funding_rate_pct": funding_rate_pct,
        "hours": float(hours),
        "estimated_per_period_usd": round(per_period, 4),
        "estimated_daily_usd": round(daily, 4),
        "note": "display_only_not_trade_signal",
    }
