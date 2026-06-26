"""Grid trading — spaced RSI entries (T11, CM-2)."""

from __future__ import annotations

from trendalgo.risk.strategy_mixins import RiskGuardMixin
from trendalgo.strategies.runtime.base import BaseNativeStrategy
from trendalgo.strategies.runtime.contract import Position, Signal, StrategyContext
from trendalgo.strategies.runtime.indicators import rsi


class GridTradingStrategy(BaseNativeStrategy, RiskGuardMixin):
    strategy_id = "grid-trading"
    timeframe = "5m"
    startup_candle_count = 30
    grid_spacing_pct = 0.02
    grid_size_usd = 25.0

    def populate_indicators(self, ctx: StrategyContext) -> None:
        df = ctx.dataframe.copy()
        if len(df) < 2:
            return
        df["rsi"] = rsi(df["close"], 14)
        df["grid_low"] = df["close"] * (1 - self.grid_spacing_pct)
        ctx.dataframe = df
        self._rows = df.to_dict("records")

    def signal(self, ctx: StrategyContext) -> Signal | None:
        df = ctx.dataframe
        if len(df) < self.startup_candle_count:
            return None
        row = df.iloc[-1]
        if row["rsi"] >= 40:
            return None
        capped = min(
            self.grid_size_usd,
            self.risk_custom_stake_amount(
                ctx.pair, None, float(row["close"]), self.grid_size_usd,
                None, None, 1, None, "long",
            ),
        )
        if capped <= 0:
            return None
        return Signal(side="long", stake_usd=capped, rationale="grid rsi entry")

    def exit(self, ctx: StrategyContext, position: Position) -> bool:
        df = ctx.dataframe
        if len(df) < 14:
            return False
        return bool(df.iloc[-1]["rsi"] > 58)
