"""Native backtest adapter tests (S15 CM-1)."""

from pathlib import Path

from trendalgo.risk.journal import TradeJournal
from trendalgo.strategies.runtime.contract import Candle
from trendalgo.strategies.runtime.loader import load_strategy
from trendalgo.trading.backtest.native_adapter import run_native_backtest


def _series(start: float, steps: int, drift: float) -> list[Candle]:
    candles: list[Candle] = []
    price = start
    for i in range(steps):
        price *= 1 + drift
        candles.append(
            Candle(
                timestamp_ms=i * 300_000,
                open=price,
                high=price * 1.01,
                low=price * 0.99,
                close=price,
                volume=100,
            )
        )
    return candles


def test_native_backtest_returns_result(tmp_path: Path) -> None:
    strategy = load_strategy("grid-trading")
    candles = _series(100.0, 80, -0.002) + _series(84.0, 40, 0.003)
    journal = TradeJournal(tmp_path / "journal.db")
    result = run_native_backtest(
        strategy,
        candles,
        pair="BTC/USD",
        exchange_id="binanceus",
        journal=journal,
    )
    assert result.metadata["engine"] == "native"
    assert result.metadata["exchange_id"] == "binanceus"
    assert result.pair == "BTC/USD"
