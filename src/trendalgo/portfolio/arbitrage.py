"""Cross-exchange arbitrage detector — read-only, informational (T35)."""

from __future__ import annotations

from typing import Any

DISCLAIMER = "Informational only. Not a trade signal. TrendAlgo does not execute arbitrage trades."


def detect_arbitrage_opportunities(
    *,
    dry_run: bool = True,
    min_spread_pct: float = 0.002,
) -> dict[str, Any]:
    """Compare sample Kraken vs Binance.US prices for major pairs."""
    if dry_run:
        pairs = [
            {"pair": "BTC/USD", "kraken": 50000.0, "binanceus": 50120.0},
            {"pair": "ETH/USD", "kraken": 3000.0, "binanceus": 2995.0},
            {"pair": "SOL/USD", "kraken": 150.0, "binanceus": 150.8},
        ]
    else:
        pairs = [
            {"pair": "BTC/USD", "kraken": 50000.0, "binanceus": 50050.0},
        ]

    alerts: list[dict[str, Any]] = []
    for row in pairs:
        low = min(row["kraken"], row["binanceus"])
        high = max(row["kraken"], row["binanceus"])
        spread_pct = (high - low) / low if low else 0.0
        if spread_pct >= min_spread_pct:
            buy_on = "kraken" if row["kraken"] < row["binanceus"] else "binanceus"
            sell_on = "binanceus" if buy_on == "kraken" else "kraken"
            alerts.append(
                {
                    "pair": row["pair"],
                    "spread_pct": round(spread_pct, 4),
                    "buy_exchange": buy_on,
                    "sell_exchange": sell_on,
                    "kraken_price": row["kraken"],
                    "binanceus_price": row["binanceus"],
                    "informational_only": True,
                }
            )

    return {
        "alerts": alerts,
        "disclaimer": DISCLAIMER,
        "auto_trade": False,
        "count": len(alerts),
    }
