"""Load native strategy instances by template id."""

from __future__ import annotations

from trendalgo.strategies.runtime.base import BaseNativeStrategy
from trendalgo.strategies.runtime.grid_trading import GridTradingStrategy
from trendalgo.strategies.runtime.macd_kraken_1h import MacdKraken1hStrategy
from trendalgo.strategies.runtime.multi_tf import MultiTFExampleStrategy
from trendalgo.strategies.runtime.smart_dca import SmartDCAStrategy

_ALIASES: dict[str, type[BaseNativeStrategy]] = {
    "multi-tf-example": MultiTFExampleStrategy,
    "strong-uptrend-scanner": MultiTFExampleStrategy,
    "multi-tf-ta": MultiTFExampleStrategy,
    "smart-dca": SmartDCAStrategy,
    "grid-trading": GridTradingStrategy,
    "macd-kraken-1h": MacdKraken1hStrategy,
}


def load_strategy(strategy_id: str) -> BaseNativeStrategy:
    cls = _ALIASES.get(strategy_id)
    if cls is None:
        raise KeyError(f"unknown native strategy: {strategy_id}")
    return cls()


def supported_strategy_ids() -> list[str]:
    return sorted(_ALIASES.keys())
