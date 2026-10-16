"""Live order sizing (E1): USD order size to base units, checked against exchange minimums."""

from __future__ import annotations

import math
from typing import Any

MAX_TICKER_AGE_S = 30.0


class OrderSizingError(ValueError):
    """An order cannot be sized safely. Live orders must not be sent when this is raised."""


def base_amount_from_usd(amount_usd: float, price: float) -> float:
    """Convert a USD order size to base-asset units at a real reference price."""
    if not math.isfinite(amount_usd) or amount_usd <= 0:
        raise OrderSizingError(f"order size must be a positive USD amount, got {amount_usd!r}")
    if not math.isfinite(price) or price <= 0:
        raise OrderSizingError(f"reference price must be positive, got {price!r}")
    return amount_usd / price


def mid_price(ticker: dict[str, Any]) -> float | None:
    """Mid of bid and ask, or None when either side is missing."""
    bid, ask = ticker.get("bid"), ticker.get("ask")
    if bid is None or ask is None:
        return None
    return (float(bid) + float(ask)) / 2


def check_ticker_fresh(
    timestamp_ms: float | None,
    now_ms: float,
    *,
    max_age_s: float = MAX_TICKER_AGE_S,
) -> None:
    """Reject a ticker with no timestamp, or one more than max_age_s from the local clock."""
    if timestamp_ms is None or not math.isfinite(timestamp_ms):
        raise OrderSizingError("ticker has no timestamp, so its freshness cannot be checked")
    age_s = (now_ms - timestamp_ms) / 1000
    if abs(age_s) > max_age_s:
        raise OrderSizingError(
            f"ticker is {age_s:.0f} s from the local clock; the limit is {max_age_s:.0f} s"
        )


def check_exchange_minimums(
    base_amount: float,
    price: float,
    *,
    min_amount: float | None,
    min_cost: float | None,
) -> None:
    """Reject an order below the market's minimum base amount or minimum cost."""
    if base_amount <= 0:
        raise OrderSizingError("order rounds to zero base units after exchange precision")
    if min_amount is not None and base_amount < min_amount:
        raise OrderSizingError(
            f"order of {base_amount} is below the exchange minimum of {min_amount}"
        )
    notional = base_amount * price
    if min_cost is not None and notional < min_cost:
        raise OrderSizingError(
            f"order value {notional:.2f} is below the exchange minimum cost of {min_cost}"
        )
