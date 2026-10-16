"""Pool jobs: candle loading, the backtest run, and clear errors when candles are missing."""

from __future__ import annotations

import math
from collections.abc import Callable
from pathlib import Path

import pytest

from trendalgo.device.jobs import (
    MIN_BARS,
    RESULT_TRADES,
    NoCandlesError,
    backtest_frame,
    backtest_job,
    load_candles,
    synthetic_frame,
)


def test_synthetic_frame_is_valid_and_repeatable() -> None:
    frame = synthetic_frame(50)
    assert list(frame.columns) == ["open", "high", "low", "close", "volume"]
    assert len(frame) == 50
    assert frame.isna().sum().sum() == 0
    assert frame.equals(synthetic_frame(50))


def test_a_missing_candle_file_is_a_no_candles_error(tmp_path: Path) -> None:
    with pytest.raises(NoCandlesError, match="no candle file for BTC/USD 1h"):
        load_candles(tmp_path / "absent.db", pair="BTC/USD", timeframe="1h")


def test_too_few_bars_is_a_no_candles_error(
    seed: Callable[..., Path],
) -> None:
    path = seed(bars=MIN_BARS - 1)
    with pytest.raises(NoCandlesError, match=f"{MIN_BARS - 1} bars"):
        load_candles(path, pair="BTC/USD", timeframe="1h")


def test_load_candles_returns_utc_bars_oldest_first(seed: Callable[..., Path]) -> None:
    path = seed(bars=MIN_BARS + 5)
    frame = load_candles(path, pair="BTC/USD", timeframe="1h")
    assert len(frame) == MIN_BARS + 5
    assert str(frame.index.tz) == "UTC"
    assert frame.index.is_monotonic_increasing
    assert list(frame.columns) == ["open", "high", "low", "close", "volume"]


def test_backtest_frame_returns_plain_values_with_or_without_the_stop() -> None:
    frame = synthetic_frame(300)
    for stop in (0.0, 5.0):
        result = backtest_frame(frame, indicator="RSI", trailing_stop_pct=stop)
        assert math.isfinite(result["final_equity"])
        assert len(result["trades"]) == min(result["total_trades"], RESULT_TRADES)


def test_backtest_frame_refuses_an_unknown_indicator() -> None:
    with pytest.raises(ValueError, match="Unknown indicator"):
        backtest_frame(synthetic_frame(300), indicator="NOT A THING", trailing_stop_pct=5.0)


def test_four_hour_history_of_180_bars_runs(seed: Callable[..., Path]) -> None:
    """BTC 4h has 180 bars in the store. Device backtests need MIN_BARS, so this must run."""
    path = seed(bars=180, timeframe="4h")
    result = backtest_job(path, "BTC/USD", "4h", "SMA Crossover", 0.0)
    assert math.isfinite(result["net_pct"])


def test_backtest_job_reads_the_candle_file_and_runs(seed: Callable[..., Path]) -> None:
    path = seed()
    result = backtest_job(path, "BTC/USD", "1h", "MACD", 5.0)
    assert math.isfinite(result["net_pct"])
    assert set(result) == {"final_equity", "net_pct", "total_trades", "win_pct", "trades"}
