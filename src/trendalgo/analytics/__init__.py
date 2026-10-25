"""Performance metrics and Market Context analytics."""

from trendalgo.analytics.market_context import MarketContext, compute_market_context
from trendalgo.analytics.metrics import PerformanceMetrics, compute_metrics, equity_curve

__all__ = [
    "MarketContext",
    "PerformanceMetrics",
    "compute_market_context",
    "compute_metrics",
    "equity_curve",
]
