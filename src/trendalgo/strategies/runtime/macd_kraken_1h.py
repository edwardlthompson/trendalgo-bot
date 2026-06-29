"""MACD crossover bot for Kraken BTC/USD on 1h (TA-Lib MACD semantics via pandas)."""

from __future__ import annotations

from trendalgo.strategies.runtime.base import BaseNativeStrategy
from trendalgo.strategies.runtime.contract import Position, Signal, StrategyContext
from trendalgo.strategies.runtime.indicators import close_series, macd


class MacdKraken1hStrategy(BaseNativeStrategy):
    strategy_id = "macd-kraken-1h"
    timeframe = "1h"
    startup_candle_count = 40
    default_stake_usd = 25.0
    exchange_id = "kraken"
    pair_default = "BTC/USD"

    def populate_indicators(self, ctx: StrategyContext) -> None:
        df = ctx.dataframe
        if len(df) < 2:
            return
        df = df.copy()
        m, sig, hist = macd(close_series(df), fastperiod=12, slowperiod=26, signalperiod=9)
        df["macd"] = m
        df["macd_signal"] = sig
        df["macd_hist"] = hist
        ctx.dataframe = df
        self._rows = df.to_dict("records")

    def signal(self, ctx: StrategyContext) -> Signal | None:
        df = ctx.dataframe
        if len(df) < self.startup_candle_count:
            return None
        row = df.iloc[-1]
        prev = df.iloc[-2]
        cross_up = prev["macd"] <= prev["macd_signal"] and row["macd"] > row["macd_signal"]
        if not cross_up:
            return None
        stake = min(
            self.default_stake_usd,
            ctx.wallet_usd * 0.1 if ctx.wallet_usd else self.default_stake_usd,
        )
        if stake <= 0:
            return None
        return Signal(
            side="long",
            stake_usd=stake,
            rationale="macd cross up 1h kraken",
        )

    def exit(self, ctx: StrategyContext, position: Position) -> bool:
        df = ctx.dataframe
        if len(df) < 2:
            return False
        row = df.iloc[-1]
        prev = df.iloc[-2]
        return bool(prev["macd"] >= prev["macd_signal"] and row["macd"] < row["macd_signal"])
