"""Multi-timeframe RSI + EMA example (ported from MultiTFExample, CM-2)."""

from __future__ import annotations

from trendalgo.lts.mixins import TrendSpotterMixin
from trendalgo.risk.strategy_mixins import RiskGuardMixin, ScalePositionMixin
from trendalgo.strategies.runtime.base import BaseNativeStrategy
from trendalgo.strategies.runtime.contract import Position, Signal, StrategyContext
from trendalgo.strategies.runtime.indicators import ema, rsi


class MultiTFExampleStrategy(
    BaseNativeStrategy, TrendSpotterMixin, RiskGuardMixin, ScalePositionMixin
):
    strategy_id = "multi-tf-example"
    timeframe = "5m"
    informative_timeframe = "1h"
    startup_candle_count = 50
    lts_uniform_min = 0.55
    default_stake_usd = 20.0

    def populate_indicators(self, ctx: StrategyContext) -> None:
        df = ctx.dataframe
        if len(df) < 2:
            return
        df = df.copy()
        df["rsi"] = rsi(df["close"], 14)
        df["ema20"] = ema(df["close"], 20)
        if ctx.informative_df is not None and len(ctx.informative_df) >= 14:
            inf = ctx.informative_df.copy()
            inf["rsi_1h"] = rsi(inf["close"], 14)
            df["rsi_1h"] = inf["rsi_1h"].iloc[-1]
        else:
            df["rsi_1h"] = df["rsi"]
        df["lts_uniform"] = self.lts_uniform_score(df.rename(columns={"timestamp_ms": "date"}))
        ctx.dataframe = df
        self._rows = df.to_dict("records")

    def signal(self, ctx: StrategyContext) -> Signal | None:
        df = ctx.dataframe
        if len(df) < self.startup_candle_count:
            return None
        row = df.iloc[-1]
        prev = df.iloc[-2]
        if (
            row["rsi"] < 35
            and row["ema20"] > prev["ema20"]
            and row.get("rsi_1h", 50) < 40
            and row.get("lts_uniform", 0) >= self.lts_uniform_min
        ):
            stake = self.risk_custom_stake_amount(
                ctx.pair,
                None,
                float(row["close"]),
                self.default_stake_usd,
                None,
                None,
                1,
                None,
                "long",
            )
            if stake <= 0:
                return None
            return Signal(side="long", stake_usd=stake, rationale="multi-tf rsi+ema+lts")
        return None

    def exit(self, ctx: StrategyContext, position: Position) -> bool:
        df = ctx.dataframe
        if len(df) < 14:
            return False
        return bool(df.iloc[-1]["rsi"] > 65)
