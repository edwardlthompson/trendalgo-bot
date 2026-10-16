"""Pool jobs (D1): plain functions that run in a worker. No Qt and no UI state; results are dicts."""

from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from trendalgo.lts_vendor.backtesting.engine import run_backtest
from trendalgo.lts_vendor.backtesting.models import BacktestConfig
from trendalgo.lts_vendor.backtesting.signals import generate_indicator_signals
from trendalgo.market.ohlcv_cache import OhlcvCache
from trendalgo.market.symbols import base_symbol

CANDLE_SOURCE = "kraken"
# The shortest history a device backtest runs on. The longest live indicator warm-up is 50 bars
# (SMA Crossover, long period 50), so 100 leaves room for trades. BTC 4h has 180 bars (D-03).
MIN_BARS = 100
RESULT_TRADES = 50
EPOCH = datetime(1970, 1, 1)
FAR_FUTURE = datetime(2100, 1, 1)


class NoCandlesError(RuntimeError):
    """The candle store has too few bars for this pair and timeframe."""


def sleep_job(seconds: float) -> float:
    """Waits. Used to test that cancel stops a job that is still running."""
    time.sleep(seconds)
    return seconds


def synthetic_frame(bars: int = 400, *, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, 0.01, bars)))
    high = close * (1.0 + np.abs(rng.normal(0.0, 0.004, bars)))
    low = close * (1.0 - np.abs(rng.normal(0.0, 0.004, bars)))
    open_ = np.concatenate(([close[0]], close[:-1]))
    volume = rng.uniform(1_000.0, 10_000.0, bars)
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close, "volume": volume})


def load_candles(candles_db: Path, *, pair: str, timeframe: str) -> pd.DataFrame:
    """OHLCV bars for one pair and timeframe, oldest first. Missing or short data raises.

    The API keys bars by base symbol (BTC/USD is stored as BTC), so the lookup uses the same rule.
    """
    if not candles_db.is_file():
        raise NoCandlesError(f"no candle file for {pair} {timeframe}")
    symbol = base_symbol(pair)
    points = OhlcvCache(candles_db).query(CANDLE_SOURCE, symbol, timeframe, EPOCH, FAR_FUTURE)
    if len(points) < MIN_BARS:
        raise NoCandlesError(f"{len(points)} bars for {pair} {timeframe}")
    index = pd.to_datetime([p.time for p in points], unit="s", utc=True)
    return pd.DataFrame(
        {
            "open": [p.open for p in points],
            "high": [p.high for p in points],
            "low": [p.low for p in points],
            "close": [p.close for p in points],
            "volume": [p.volume for p in points],
        },
        index=index,
    )


def backtest_frame(
    frame: pd.DataFrame,
    *,
    indicator: str,
    trailing_stop_pct: float,
) -> dict[str, Any]:
    """Run one indicator over the frame. Returns plain values so the result crosses processes."""
    buy, sell = generate_indicator_signals(indicator, frame)
    config = BacktestConfig(
        trailing_stop_loss_pct=trailing_stop_pct,
        trailing_stop_enabled=trailing_stop_pct > 0,
    )
    result = run_backtest(frame, buy, sell, config)
    trades = [
        {
            "entry_time": str(t.entry_time),
            "exit_time": str(t.exit_time),
            "entry_price": float(t.entry_price),
            "exit_price": float(t.exit_price),
            "pnl_pct": float(t.pnl_pct),
            "exit_reason": str(t.exit_reason),
        }
        for t in result.trades[-RESULT_TRADES:]
    ]
    return {
        "final_equity": float(result.final_equity),
        "net_pct": float(result.net_pct),
        "total_trades": int(result.total_trades),
        "win_pct": float(result.win_pct),
        "trades": trades,
    }


def backtest_job(
    candles_db: Path,
    pair: str,
    timeframe: str,
    indicator: str,
    trailing_stop_pct: float,
) -> dict[str, Any]:
    frame = load_candles(candles_db, pair=pair, timeframe=timeframe)
    return backtest_frame(frame, indicator=indicator, trailing_stop_pct=trailing_stop_pct)


def engine_check_job(seed: int) -> dict[str, Any]:
    """A backtest on synthetic bars. The self-test runs it in a worker to prove the engine loads."""
    return backtest_frame(synthetic_frame(seed=seed), indicator="RSI", trailing_stop_pct=5.0)
