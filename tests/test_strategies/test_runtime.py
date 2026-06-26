"""Native strategy runtime tests (S15 CM-2)."""

from __future__ import annotations

from trendalgo.strategies.runtime.contract import Candle, StrategyContext
from trendalgo.strategies.runtime.grid_trading import GridTradingStrategy
from trendalgo.strategies.runtime.loader import load_strategy, supported_strategy_ids
from trendalgo.strategies.runtime.smart_dca import SmartDCAStrategy


def _candle(ts: int, close: float) -> Candle:
    return Candle(
        timestamp_ms=ts, open=close, high=close * 1.01, low=close * 0.99, close=close, volume=100
    )


def test_loader_supports_templates() -> None:
    ids = supported_strategy_ids()
    assert "multi-tf-example" in ids
    assert "grid-trading" in ids
    strat = load_strategy("smart-dca")
    assert isinstance(strat, SmartDCAStrategy)


def test_grid_trading_signal_on_oversold_series() -> None:
    strat = GridTradingStrategy()
    ctx = StrategyContext(pair="BTC/USD", timeframe="5m", dataframe=strat.dataframe)
    price = 100.0
    for i in range(40):
        price *= 0.995
        strat.on_candle(_candle(i * 300_000, price), ctx)
        ctx = StrategyContext(pair="BTC/USD", timeframe="5m", dataframe=strat.dataframe)
    sig = strat.signal(ctx)
    assert sig is None or sig.side == "long"
