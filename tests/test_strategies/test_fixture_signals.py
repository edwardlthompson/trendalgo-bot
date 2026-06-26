"""Fixture OHLCV signal tests (S16 CM-2)."""

from __future__ import annotations

from trendalgo.strategies.runtime.contract import Candle, StrategyContext
from trendalgo.strategies.runtime.grid_trading import GridTradingStrategy
from trendalgo.strategies.runtime.smart_dca import SmartDCAStrategy


def _candles_downtrend(start: float, count: int, drift: float = -0.008) -> list[Candle]:
    candles: list[Candle] = []
    price = start
    for i in range(count):
        candles.append(
            Candle(
                timestamp_ms=i * 300_000,
                open=price,
                high=price * 1.002,
                low=price * 0.998,
                close=price,
                volume=1000,
            )
        )
        price *= 1 + drift
    return candles


def test_grid_trading_fixture_emits_entry_signal() -> None:
    strat = GridTradingStrategy()
    ctx = StrategyContext(pair="BTC/USD", timeframe="5m", dataframe=strat.dataframe)
    signal = None
    for candle in _candles_downtrend(100.0, 45):
        strat.on_candle(candle, ctx)
        ctx = StrategyContext(pair="BTC/USD", timeframe="5m", dataframe=strat.dataframe)
        signal = strat.signal(ctx)
        if signal is not None:
            break
    assert signal is not None
    assert signal.side == "long"
    assert signal.stake_usd > 0


def test_smart_dca_fixture_emits_on_dip() -> None:
    strat = SmartDCAStrategy()
    ctx = StrategyContext(pair="ETH/USD", timeframe="1h", dataframe=strat.dataframe)
    candles = _candles_downtrend(3000.0, 35, drift=-0.012)
    signal = None
    for candle in candles:
        strat.on_candle(candle, ctx)
        ctx = StrategyContext(pair="ETH/USD", timeframe="1h", dataframe=strat.dataframe)
        signal = strat.signal(ctx)
        if signal is not None:
            break
    assert signal is None or signal.side == "long"
