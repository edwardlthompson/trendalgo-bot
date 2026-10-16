"""Live order helpers that talk to the exchange: precision, minimums, and lookup (E2, E3)."""

from __future__ import annotations

import time
from typing import Any

from trendalgo.trading.sizing import check_exchange_minimums

LOOKUP_WINDOW_S = 600.0


def precise_amount(exchange: Any, pair: str, base: float, price: float) -> float:
    """Round the base size down to the market precision, then enforce exchange minimums."""
    exchange.load_markets()
    limits = exchange.market(pair).get("limits") or {}
    amount_limits = limits.get("amount") or {}
    cost_limits = limits.get("cost") or {}
    rounded = float(exchange.amount_to_precision(pair, base))
    check_exchange_minimums(
        rounded,
        price,
        min_amount=amount_limits.get("min"),
        min_cost=cost_limits.get("min"),
    )
    return rounded


def find_by_client_id(
    exchange: Any, pair: str, client_id: str, *, since_ms: int | None = None
) -> dict[str, Any] | None:
    """Search open, then closed, orders for our client id. Closed orders are read from since_ms."""
    since = int((time.time() - LOOKUP_WINDOW_S) * 1000) if since_ms is None else since_ms
    for fetch in (exchange.fetch_open_orders, exchange.fetch_closed_orders):
        for order in fetch(pair, since) or []:
            if order.get("clientOrderId") == client_id:
                return dict(order)
    return None
