"""Smart DCA — interval buys with dip acceleration (T9, CM-2)."""

from __future__ import annotations

from trendalgo.risk.strategy_mixins import RiskGuardMixin
from trendalgo.strategies.runtime.base import BaseNativeStrategy
from trendalgo.strategies.runtime.contract import Position, Signal, StrategyContext
from trendalgo.strategies.runtime.indicators import rsi


class SmartDCAStrategy(BaseNativeStrategy, RiskGuardMixin):
    strategy_id = "smart-dca"
    timeframe = "1h"
    startup_candle_count = 30
    dca_amount_usd = 50.0
    dip_pct = 0.03

    def populate_indicators(self, ctx: StrategyContext) -> None:
        df = ctx.dataframe.copy()
        if len(df) < 2:
            return
        df["rsi"] = rsi(df["close"], 14)
        df["dip"] = (df["close"] / df["close"].shift(24) - 1) < -self.dip_pct
        ctx.dataframe = df
        self._rows = df.to_dict("records")

    def signal(self, ctx: StrategyContext) -> Signal | None:
        df = ctx.dataframe
        if len(df) < self.startup_candle_count:
            return None
        row = df.iloc[-1]
        if not (row["rsi"] < 45 or bool(row.get("dip", False))):
            return None
        capped = min(
            self.dca_amount_usd,
            self.risk_custom_stake_amount(
                ctx.pair,
                None,
                float(row["close"]),
                self.dca_amount_usd,
                None,
                None,
                1,
                None,
                "long",
            ),
        )
        if capped <= 0:
            return None
        return Signal(side="long", stake_usd=capped, rationale="smart-dca dip or rsi")

    def exit(self, ctx: StrategyContext, position: Position) -> bool:
        df = ctx.dataframe
        if len(df) < 14:
            return False
        return bool(df.iloc[-1]["rsi"] > 70)
