"""Cross-exchange arbitrage detector — read-only, informational (T35, S19 multi-venue)."""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, wait
from typing import Any

import ccxt

from trendalgo.exchanges.registry import ExchangeEntry, list_trading_exchanges

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


def _ticker_price(ticker: dict[str, Any]) -> float | None:
    for field in ("last", "close", "bid", "ask"):
        value = ticker.get(field)
        if isinstance(value, (int, float)) and value > 0:
            return float(value)
    return None


def _fetch_venue(entry: ExchangeEntry, timeout_ms: int) -> dict[str, float]:
    exchange_class = getattr(ccxt, entry.ccxt_id, None)
    if exchange_class is None:
        raise ValueError(f"ccxt has no exchange class: {entry.ccxt_id}")
    client = exchange_class({"enableRateLimit": True, "timeout": timeout_ms})
    tickers = client.fetch_tickers(list(_PAIRS))
    return {
        pair: price
        for pair in _PAIRS
        if isinstance((ticker := tickers.get(pair)), dict)
        and (price := _ticker_price(ticker)) is not None
    }


def _live_price_matrix(
    entries: list[ExchangeEntry],
) -> tuple[dict[str, dict[str, float]], list[str], dict[str, str]]:
    budget = max(0.01, float(os.environ.get("ARBITRAGE_TIMEOUT_SECONDS", "8")))
    executor = ThreadPoolExecutor(max_workers=len(entries), thread_name_prefix="arb-price")
    future_to_id = {
        executor.submit(_fetch_venue, entry, int(budget * 1000)): entry.id for entry in entries
    }
    done, pending = wait(future_to_id, timeout=budget)
    timed_out = sorted(future_to_id[future] for future in pending)
    for future in pending:
        future.cancel()
    matrix: dict[str, dict[str, float]] = {}
    failures: dict[str, str] = {}
    for future in done:
        venue = future_to_id[future]
        try:
            prices = future.result()
            if prices:
                matrix[venue] = prices
            else:
                failures[venue] = "no supported ticker prices"
        except Exception as exc:
            failures[venue] = str(exc)
    executor.shutdown(wait=False, cancel_futures=True)
    return matrix, timed_out, failures


def detect_arbitrage_opportunities(
    *,
    dry_run: bool = True,
    min_spread_pct: float = 0.002,
) -> dict[str, Any]:
    """Compare sample prices across all registry trading venues for major pairs."""
    entries = list_trading_exchanges()
    trading_ids = {entry.id for entry in entries}
    timed_out: list[str] = []
    failures: dict[str, str] = {}
    matrix = _DRY_RUN_MATRIX
    source = "dry_run"
    if not dry_run:
        matrix, timed_out, failures = _live_price_matrix(entries)
        source = "live"
        if not matrix:
            matrix = _DRY_RUN_MATRIX
            source = "dry_run_fallback"
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
        "pricing_source": source,
        "timed_out_venues": timed_out,
        "failed_venues": failures,
    }
