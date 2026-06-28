"""MACD Kraken 1h native strategy smoke tests."""

from pathlib import Path

import pandas as pd

from trendalgo.risk.journal import TradeJournal
from trendalgo.strategies.runtime.indicators import macd
from trendalgo.strategies.runtime.loader import load_strategy
from trendalgo.trading.backtest.native_adapter import run_native_backtest
from trendalgo.trading.backtest.walk_forward import fixture_candles


def test_macd_indicator_returns_three_series() -> None:
    close = pd.Series([100.0 + i * 0.5 for i in range(50)])
    m, s, h = macd(close)
    assert len(m) == 50
    assert len(s) == 50
    assert len(h) == 50


def test_macd_kraken_1h_native_backtest(tmp_path: Path) -> None:
    strategy = load_strategy("macd-kraken-1h")
    assert strategy.timeframe == "1h"
    candles = fixture_candles(count=120, start=50_000.0, drift=0.0003, interval_ms=3_600_000)
    journal = TradeJournal(tmp_path / "macd-journal.db")
    result = run_native_backtest(
        strategy,
        candles,
        pair="BTC/USD",
        exchange_id="kraken",
        journal=journal,
    )
    assert result.metadata["engine"] == "native"
    assert result.metadata["exchange_id"] == "kraken"
    assert result.timeframe == "1h"
