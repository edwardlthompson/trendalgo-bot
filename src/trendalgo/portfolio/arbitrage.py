"""Cross-exchange arbitrage detector — read-only, informational (T35, S19 multi-venue)."""

from __future__ import annotations

from typing import Any

from trendalgo.exchanges.registry import list_trading_exchanges

DISCLAIMER = "Informational only. Not a trade signal. TrendAlgo does not execute arbitrage trades."

_PAIRS = ("BTC/USD", "ETH/USD", "SOL/USD")

_DRY_RUN_MATRIX: dict[str, dict[str, float]] = {
    "kraken": {"BTC/USD": 50000.0, "ETH/USD": 3000.0, "SOL/USD": 150.0},
    "binanceus": {"BTC/USD": 50120.0, "ETH/USD": 2995.0, "SOL/USD": 150.8},
    "coinbaseadvanced": {"BTC/USD": 50080.0, "ETH/USD": 3005.0, "SOL/USD": 150.2},
    "gemini": {"BTC/USD": 49990.0, "ETH/USD": 2998.0, "SOL/USD": 149.9},
    "bitstamp": {"BTC/USD": 50040.0, "ETH/USD": 3002.0, "SOL/USD": 150.5},
    "cryptocom": {"BTC/USD": 50100.0, "ETH/USD": 2990.0, "SOL/USD": 150.6},
    "binance": {"BTC/USD": 50150.0, "ETH/USD": 2992.0, "SOL/USD": 151.0},
    "bybit": {"BTC/USD": 50060.0, "ETH/USD": 3008.0, "SOL/USD": 150.3},
    "okx": {"BTC/USD": 50030.0, "ETH/USD": 3001.0, "SOL/USD": 150.1},
}

_LIVE_MATRIX: dict[str, dict[str, float]] = {
    "kraken": {"BTC/USD": 50000.0, "ETH/USD": 3000.0},
    "binanceus": {"BTC/USD": 50050.0, "ETH/USD": 3002.0},
    "coinbaseadvanced": {"BTC/USD": 50025.0, "ETH/USD": 3001.0},
    "gemini": {"BTC/USD": 50010.0, "ETH/USD": 2999.0},
    "bitstamp": {"BTC/USD": 50020.0, "ETH/USD": 3000.5},
    "cryptocom": {"BTC/USD": 50035.0, "ETH/USD": 3001.5},
    "binance": {"BTC/USD": 50045.0, "ETH/USD": 3003.0},
    "bybit": {"BTC/USD": 50015.0, "ETH/USD": 2998.5},
    "okx": {"BTC/USD": 50030.0, "ETH/USD": 3000.0},
}


def _price_matrix(*, dry_run: bool) -> dict[str, dict[str, float]]:
    return _DRY_RUN_MATRIX if dry_run else _LIVE_MATRIX


def detect_arbitrage_opportunities(
    *,
    dry_run: bool = True,
    min_spread_pct: float = 0.002,
) -> dict[str, Any]:
    """Compare sample prices across all registry trading venues for major pairs."""
    trading_ids = {entry.id for entry in list_trading_exchanges()}
    matrix = _price_matrix(dry_run=dry_run)
    alerts: list[dict[str, Any]] = []

    for pair in _PAIRS:
        prices: dict[str, float] = {
            exchange_id: matrix[exchange_id][pair]
            for exchange_id in trading_ids
            if exchange_id in matrix and pair in matrix[exchange_id]
        }
        if len(prices) < 2:
            continue

        buy_on = min(prices, key=lambda k: prices[k])
        sell_on = max(prices, key=lambda k: prices[k])
        low = prices[buy_on]
        high = prices[sell_on]
        spread_pct = (high - low) / low if low else 0.0
        if spread_pct < min_spread_pct:
            continue

        alerts.append(
            {
                "pair": pair,
                "spread_pct": round(spread_pct, 4),
                "buy_exchange": buy_on,
                "sell_exchange": sell_on,
                "prices": {exchange_id: prices[exchange_id] for exchange_id in sorted(prices)},
                "venues_compared": len(prices),
                "informational_only": True,
            }
        )

    alerts.sort(key=lambda row: row["spread_pct"], reverse=True)
    return {
        "alerts": alerts,
        "disclaimer": DISCLAIMER,
        "auto_trade": False,
        "count": len(alerts),
        "venues": sorted(trading_ids),
    }
