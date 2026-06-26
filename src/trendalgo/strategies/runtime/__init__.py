"""Native strategy runtime (ADR-0010)."""

from trendalgo.strategies.runtime.contract import (
    Candle,
    NativeStrategy,
    Position,
    Signal,
    StrategyContext,
)
from trendalgo.strategies.runtime.loader import load_strategy, supported_strategy_ids

__all__ = [
    "Candle",
    "NativeStrategy",
    "Position",
    "Signal",
    "StrategyContext",
    "load_strategy",
    "supported_strategy_ids",
]
