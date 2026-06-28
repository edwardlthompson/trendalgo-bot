"""Native backtest walk-forward (CM-3, S17)."""

from __future__ import annotations

from typing import Any

from trendalgo.strategies.runtime.contract import Candle
from trendalgo.strategies.runtime.loader import load_strategy
from trendalgo.trading.backtest.native_adapter import run_native_backtest


def fixture_candles(
    *,
    count: int = 120,
    start: float = 100.0,
    drift: float = -0.003,
    interval_ms: int = 300_000,
) -> list[Candle]:
    """Deterministic price series for walk-forward folds and TA sweeps."""
    candles: list[Candle] = []
    price = start
    for i in range(count):
        phase_drift = drift if i < count // 2 else abs(drift) * 0.8
        candles.append(
            Candle(
                timestamp_ms=i * interval_ms,
                open=price,
                high=price * 1.005,
                low=price * 0.995,
                close=price,
                volume=1000.0,
            )
        )
        price *= 1 + phase_drift
    return candles


def run_native_walk_forward(
    strategy_id: str,
    candles: list[Candle],
    *,
    pair: str = "BTC/USD",
    exchange_id: str = "kraken",
    train_size: int = 40,
    test_size: int = 20,
) -> dict[str, Any]:
    """Split OHLCV into train/test windows; score each fold via native backtest."""
    if len(candles) < train_size + test_size:
        candles = fixture_candles(count=max(train_size + test_size, 80))

    strategy = load_strategy(strategy_id)
    folds: list[dict[str, Any]] = []
    i = 0
    while i + train_size + test_size <= len(candles):
        train_slice = candles[i : i + train_size]
        test_slice = candles[i + train_size : i + train_size + test_size]
        train_result = run_native_backtest(
            strategy,
            train_slice,
            pair=pair,
            exchange_id=exchange_id,
            timerange=f"train-{i}",
        )
        test_result = run_native_backtest(
            load_strategy(strategy_id),
            test_slice,
            pair=pair,
            exchange_id=exchange_id,
            timerange=f"test-{i + train_size}",
        )
        folds.append(
            {
                "fold": len(folds) + 1,
                "train_pnl": round(train_result.profit_total, 2),
                "test_pnl": round(test_result.profit_total, 2),
                "train_trades": train_result.total_trades,
                "test_trades": test_result.total_trades,
                "train_window": i,
                "test_window": i + train_size,
            }
        )
        i += test_size

    avg_test = sum(f["test_pnl"] for f in folds) / len(folds) if folds else 0.0
    return {
        "engine": "native",
        "strategy": strategy_id,
        "pair": pair,
        "folds": folds,
        "fold_count": len(folds),
        "avg_test_pnl": round(avg_test, 2),
        "status": "complete",
        "candles": len(candles),
    }
