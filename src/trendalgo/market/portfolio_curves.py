"""Portfolio chart curves from market closes."""

from __future__ import annotations

from datetime import UTC, datetime

from trendalgo.market.service import (
    PriceHistoryService,
    get_price_history_service,
    granularity_for_range,
    range_window,
)
from trendalgo.market.types import PricePoint

BTC_QTY = 1.0


def _to_chart_points(closes: list[PricePoint], quantity: float) -> list[dict[str, float | int]]:
    return [{"time": p.time, "value": round(p.close * quantity, 2)} for p in closes]


def btc_portfolio_curve(
    range_key: str,
    *,
    quantity: float = BTC_QTY,
    now: datetime | None = None,
    service: PriceHistoryService | None = None,
) -> list[dict[str, float | int]]:
    anchor = (now or datetime.now(UTC)).replace(microsecond=0)
    window = range_window(range_key)
    since = anchor - window
    tf = granularity_for_range(range_key)
    svc = service or get_price_history_service()
    closes = svc.get_closes("BTC", tf, since, anchor)
    return _to_chart_points(closes, quantity)


def token_closes_for_range(
    symbols: tuple[str, ...],
    range_key: str,
    *,
    now: datetime | None = None,
    service: PriceHistoryService | None = None,
) -> dict[str, list[PricePoint]]:
    anchor = (now or datetime.now(UTC)).replace(microsecond=0)
    since = anchor - range_window(range_key)
    tf = granularity_for_range(range_key)
    svc = service or get_price_history_service()
    return {sym: svc.get_closes(sym, tf, since, anchor) for sym in symbols}
