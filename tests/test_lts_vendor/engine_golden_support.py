"""Deterministic backtest scenarios shared by the engine golden test and its fixture writer.

Only pandas-based indicators are used so the set runs without the optional TA-Lib binding.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from trendalgo.lts_vendor.backtesting.engine import run_backtest
from trendalgo.lts_vendor.backtesting.models import BacktestConfig, BacktestResult
from trendalgo.lts_vendor.backtesting.parameter_space import PARAMETER_SPACE
from trendalgo.lts_vendor.backtesting.signals import generate_indicator_signals

INDICATORS = ("RSI", "MACD", "Bollinger %B", "EMA Crossover", "SMA Crossover", "Heikin Ashi")
SEEDS = (0, 1, 2)
BARS = (180, 720)
TSL_VALUES = (2.0, 8.0, 20.0)
RANDOM_CONFIGS = ((8.0, 0.0, 0.0), (5.0, 10.0, 0.0), (5.0, 10.0, 3.0), (1.0, 0.0, 0.0))
FIXTURE_PATH = Path(__file__).parent / "fixtures" / "engine_golden.json"


def make_frame(bars: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, 0.01, bars)))
    high = close * (1.0 + np.abs(rng.normal(0.0, 0.004, bars)))
    low = close * (1.0 - np.abs(rng.normal(0.0, 0.004, bars)))
    open_ = np.concatenate(([close[0]], close[:-1]))
    volume = rng.uniform(1_000.0, 10_000.0, bars)
    index = pd.date_range("2026-09-01", periods=bars, freq="h")
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume}, index=index
    )


def _midpoint(indicator: str) -> dict[str, Any]:
    space = PARAMETER_SPACE.get(indicator, {})
    return {key: values[len(values) // 2] for key, values in space.items()}


def _plain(result: BacktestResult) -> dict[str, Any]:
    """Exact, JSON-safe view of a result: floats as repr so no precision is lost."""
    return {
        "final_equity": repr(result.final_equity),
        "net_pct": repr(result.net_pct),
        "total_trades": result.total_trades,
        "win_pct": repr(result.win_pct),
        "trades": [
            {
                key: (repr(value) if isinstance(value, float) else value)
                for key, value in asdict(t).items()
            }
            for t in result.trades
        ],
    }


def digest(result: BacktestResult) -> str:
    blob = json.dumps(_plain(result), sort_keys=True).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def _config(tsl: float, take_profit: float = 0.0, trailing_tp: float = 0.0) -> BacktestConfig:
    return BacktestConfig(
        starting_capital=1000.0,
        fee_bps_round_trip=52.0,
        trailing_stop_loss_pct=tsl,
        take_profit_pct=take_profit,
        trailing_take_profit_pct=trailing_tp,
    )


def build_digests() -> dict[str, str]:
    """Run every scenario through the engine and return case id -> result digest."""
    digests: dict[str, str] = {}
    for seed in SEEDS:
        for bars in BARS:
            frame = make_frame(bars, seed)
            for indicator in INDICATORS:
                buy, sell = generate_indicator_signals(indicator, frame, _midpoint(indicator))
                for tsl in TSL_VALUES:
                    result = run_backtest(
                        frame=frame, buy_signals=buy, sell_signals=sell, config=_config(tsl)
                    )
                    digests[f"sig/{seed}/{bars}/{indicator}/{tsl:g}"] = digest(result)
            rng = np.random.default_rng(seed + 100)
            buy = pd.Series(rng.random(bars) < 0.1, index=frame.index)
            sell = pd.Series(rng.random(bars) < 0.05, index=frame.index)
            for tsl, take_profit, trailing_tp in RANDOM_CONFIGS:
                result = run_backtest(
                    frame=frame,
                    buy_signals=buy,
                    sell_signals=sell,
                    config=_config(tsl, take_profit, trailing_tp),
                )
                key = f"rnd/{seed}/{bars}/{tsl:g}-{take_profit:g}-{trailing_tp:g}"
                digests[key] = digest(result)
    return digests


def write_fixture() -> None:
    """Regenerate the golden fixture. Run only after an intentional, reviewed engine change."""
    FIXTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {"version": 1, "digests": build_digests()}
    FIXTURE_PATH.write_text(json.dumps(payload, indent=1, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    write_fixture()
