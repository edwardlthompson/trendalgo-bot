"""Native strategy runtime contract (ADR-0010, CM-2)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

import pandas as pd


@dataclass(frozen=True)
class Candle:
    timestamp_ms: int
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class Position:
    pair: str
    side: str
    stake_usd: float
    entry_price: float


@dataclass
class StrategyContext:
    pair: str
    timeframe: str
    dataframe: pd.DataFrame
    position: Position | None = None
    wallet_usd: float = 1000.0
    informative_df: pd.DataFrame | None = None
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True)
class Signal:
    side: str
    stake_usd: float
    rationale: str


class NativeStrategy(Protocol):
    strategy_id: str
    timeframe: str

    @property
    def dataframe(self) -> pd.DataFrame: ...

    def on_candle(self, candle: Candle, ctx: StrategyContext) -> None: ...

    def signal(self, ctx: StrategyContext) -> Signal | None: ...

    def exit(self, ctx: StrategyContext, position: Position) -> bool: ...
