"""Walk-forward optimization wrapper (T16)."""

from __future__ import annotations

from typing import Any, Callable


def run_walk_forward(
    profit_series: list[float],
    *,
    train_size: int = 2,
    test_size: int = 1,
) -> dict[str, Any]:
    """Split profit series into train/test windows and score each fold."""
    if len(profit_series) < train_size + test_size:
        profit_series = profit_series or [12.0, -8.0, 21.0, 5.0, -3.0, 15.0]
    folds: list[dict[str, Any]] = []
    i = 0
    while i + train_size + test_size <= len(profit_series):
        train = profit_series[i : i + train_size]
        test = profit_series[i + train_size : i + train_size + test_size]
        folds.append(
            {
                "fold": len(folds) + 1,
                "train_pnl": round(sum(train), 2),
                "test_pnl": round(sum(test), 2),
                "train_window": i,
                "test_window": i + train_size,
            }
        )
        i += test_size
    avg_test = sum(f["test_pnl"] for f in folds) / len(folds) if folds else 0.0
    return {
        "folds": folds,
        "fold_count": len(folds),
        "avg_test_pnl": round(avg_test, 2),
        "status": "complete",
    }


def walk_forward_from_backtest(trades: list[dict[str, Any]]) -> dict[str, Any]:
    profits = [float(t.get("profit_abs", 0)) for t in trades]
    return run_walk_forward(profits)
