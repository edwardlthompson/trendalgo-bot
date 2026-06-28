"""Rank TA indicators on BTC/USD Kraken 1h via simple crossover backtests."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from trendalgo.strategies.runtime.contract import Candle
from trendalgo.ta.catalog import all_ta_count
from trendalgo.ta.engine import talib_available
from trendalgo.ta.signals import signals_for_preset
from trendalgo.trading.backtest.walk_forward import fixture_candles

# Smoke sweep presets — each maps to TA function name(s).
SWEEP_PRESETS: tuple[dict[str, Any], ...] = (
    {"id": "MACD", "fn": "MACD", "kind": "macd_cross"},
    {"id": "RSI", "fn": "RSI", "kind": "bounded_reversal", "timeperiod": 14},
    {"id": "SMA_CROSS", "fn": "SMA", "kind": "ma_cross", "fast": 10, "slow": 30},
    {"id": "EMA_CROSS", "fn": "EMA", "kind": "ma_cross", "fast": 12, "slow": 26},
    {"id": "ROC", "fn": "ROC", "kind": "zero_cross", "timeperiod": 10},
    {"id": "MOM", "fn": "MOM", "kind": "zero_cross", "timeperiod": 10},
    {"id": "VFI", "fn": "VFI", "kind": "zero_cross", "length": 130},
    {"id": "SUPERTREND", "fn": "SUPERTREND", "kind": "price_cross", "length": 7},
)


def _candles_to_df(candles: list[Candle]) -> pd.DataFrame:
    df = pd.DataFrame(
        [
            {
                "timestamp_ms": c.timestamp_ms,
                "open": c.open,
                "high": c.high,
                "low": c.low,
                "close": c.close,
                "volume": c.volume,
            }
            for c in candles
        ]
    )
    df.index = pd.to_datetime(df["timestamp_ms"], unit="ms", utc=True)
    return df


def _simulate_long(df: pd.DataFrame, entries: np.ndarray, exits: np.ndarray) -> dict[str, float]:
    stake = 100.0
    pnl = 0.0
    trades = 0
    in_pos = False
    entry_price = 0.0
    closes = df["close"].to_numpy(dtype=float)
    for i in range(1, len(closes)):
        if not in_pos and entries[i]:
            in_pos = True
            entry_price = closes[i]
        elif in_pos and exits[i]:
            pnl += stake * ((closes[i] / entry_price) - 1)
            trades += 1
            in_pos = False
    if in_pos:
        pnl += stake * ((closes[-1] / entry_price) - 1)
        trades += 1
    return {"profit_total": round(pnl, 2), "trades": float(trades)}


def _signals_for_preset(df: pd.DataFrame, preset: dict[str, Any]) -> tuple[np.ndarray, np.ndarray]:
    return signals_for_preset(df, preset)


def trades_from_signals(
    *,
    pair: str,
    chart: list[dict[str, int | float]],
    closes: np.ndarray,
    entries: np.ndarray,
    exits: np.ndarray,
    stake: float,
) -> list[dict[str, Any]]:
    from datetime import UTC, datetime

    trades: list[dict[str, Any]] = []
    in_pos = False
    entry_idx = 0
    times = [int(chart[i]["time"]) for i in range(len(chart))]
    for i in range(1, len(closes)):
        if not in_pos:
            if bool(exits[i]):
                continue
            if bool(entries[i]):
                in_pos = True
                entry_idx = i
                trades.append(
                    {
                        "pair": pair,
                        "side": "buy",
                        "stake_usd": stake,
                        "pnl_usd": 0.0,
                        "price": float(closes[i]),
                        "created_at": datetime.fromtimestamp(times[i], tz=UTC).isoformat(),
                        "simulated": True,
                    }
                )
        elif bool(exits[i]):
            entry_px = float(closes[entry_idx])
            exit_px = float(closes[i])
            pnl = stake * ((exit_px / entry_px) - 1) if entry_px else 0.0
            trades.append(
                {
                    "pair": pair,
                    "side": "sell",
                    "stake_usd": stake,
                    "pnl_usd": round(pnl, 2),
                    "price": exit_px,
                    "created_at": datetime.fromtimestamp(times[i], tz=UTC).isoformat(),
                    "simulated": True,
                }
            )
            in_pos = False
    if trades and trades[0]["side"] != "buy":
        while trades and trades[0]["side"] == "sell":
            trades.pop(0)
    return trades


def run_ta_sweep(
    *,
    pair: str = "BTC/USD",
    exchange_id: str = "kraken",
    timeframe: str = "1h",
    candle_count: int = 200,
) -> dict[str, Any]:
    interval_ms = 3_600_000 if timeframe == "1h" else 300_000
    candles = fixture_candles(
        count=candle_count,
        start=50_000.0,
        drift=0.00025,
        interval_ms=interval_ms,
    )
    df = _candles_to_df(candles)
    ranked: list[dict[str, Any]] = []
    for preset in SWEEP_PRESETS:
        try:
            entries, exits = _signals_for_preset(df, preset)
            stats = _simulate_long(df, entries, exits)
            ranked.append(
                {
                    "indicator": preset["id"],
                    "ta_function": preset["fn"],
                    **stats,
                }
            )
        except (KeyError, ValueError, TypeError):
            continue
    ranked.sort(key=lambda r: r["profit_total"], reverse=True)
    best = ranked[0] if ranked else None
    payload = {
        "pair": pair,
        "exchange_id": exchange_id,
        "timeframe": timeframe,
        "catalog_count": all_ta_count(),
        "talib_available": talib_available(),
        "sweep_count": len(ranked),
        "best": best,
        "rankings": ranked,
        "top5": ranked[:5],
    }
    return payload
