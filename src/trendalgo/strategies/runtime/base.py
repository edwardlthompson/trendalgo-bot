"""Base native strategy with OHLCV accumulation."""

from __future__ import annotations

from typing import Any

import pandas as pd

from trendalgo.strategies.runtime.contract import Candle, StrategyContext


class BaseNativeStrategy:
    strategy_id: str = "base"
    timeframe: str = "5m"
    startup_candle_count: int = 50

    def __init__(self) -> None:
        self._rows: list[dict[str, Any]] = []

    @property
    def dataframe(self) -> pd.DataFrame:
        if not self._rows:
            return pd.DataFrame(
                columns=["timestamp_ms", "open", "high", "low", "close", "volume"]
            )
        return pd.DataFrame(self._rows)

    def on_candle(self, candle: Candle, ctx: StrategyContext) -> None:
        self._append_candle(candle)
        ctx.dataframe = self.dataframe
        self.populate_indicators(ctx)

    def populate_indicators(self, ctx: StrategyContext) -> None:
        """Override to compute indicators on ctx.dataframe."""

    def _append_candle(self, candle: Candle) -> None:
        self._rows.append(
            {
                "timestamp_ms": candle.timestamp_ms,
                "open": candle.open,
                "high": candle.high,
                "low": candle.low,
                "close": candle.close,
                "volume": candle.volume,
            }
        )
        max_rows = max(self.startup_candle_count * 4, 200)
        if len(self._rows) > max_rows:
            self._rows = self._rows[-max_rows:]
