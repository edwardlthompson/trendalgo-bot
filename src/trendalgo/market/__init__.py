"""Market data package."""

from trendalgo.market.portfolio_curves import btc_portfolio_curve, token_closes_for_range
from trendalgo.market.service import (
    DAILY_RANGES,
    HOURLY_RANGES,
    PriceHistoryService,
    get_price_history_service,
    granularity_for_range,
    range_window,
    reset_price_history_service,
)
from trendalgo.market.synthetic import btc_usd_price_at, token_usd_price_at
from trendalgo.market.types import PricePoint

__all__ = [
    "DAILY_RANGES",
    "HOURLY_RANGES",
    "PriceHistoryService",
    "PricePoint",
    "btc_portfolio_curve",
    "btc_usd_price_at",
    "get_price_history_service",
    "granularity_for_range",
    "range_window",
    "reset_price_history_service",
    "token_closes_for_range",
    "token_usd_price_at",
]
