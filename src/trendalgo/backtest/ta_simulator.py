"""Fee-aware long-only TA backtest simulator."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from trendalgo.exchanges.fees import ExchangeFeeSchedule


def simulate_long_with_fees(
    df: pd.DataFrame,
    entries: np.ndarray,
    exits: np.ndarray,
    *,
    stake_usd: float,
    fee: ExchangeFeeSchedule,
    trailing_stop_pct: float = 0.0,
) -> dict[str, Any]:
    gross = 0.0
    fees_paid = 0.0
    trades = 0
    wins = 0
    tsl_hits = 0
    in_pos = False
    entry_price = 0.0
    peak_price = 0.0
    closes = df["close"].to_numpy(dtype=float)
    fee_per_trade = fee.round_trip_taker_cost(stake_usd)
    tsl = max(0.0, trailing_stop_pct)

    for i in range(1, len(closes)):
        if not in_pos and entries[i]:
            in_pos = True
            entry_price = closes[i]
            peak_price = entry_price
        elif in_pos:
            peak_price = max(peak_price, closes[i])
            stop_hit = tsl > 0 and closes[i] <= peak_price * (1.0 - tsl)
            if exits[i] or stop_hit:
                if stop_hit:
                    tsl_hits += 1
                gross_pnl = stake_usd * ((closes[i] / entry_price) - 1.0) if entry_price else 0.0
                net_pnl = gross_pnl - fee_per_trade
                gross += gross_pnl
                fees_paid += fee_per_trade
                trades += 1
                if net_pnl > 0:
                    wins += 1
                in_pos = False
                entry_price = 0.0
                peak_price = 0.0

    if in_pos and entry_price:
        gross_pnl = stake_usd * ((closes[-1] / entry_price) - 1.0)
        net_pnl = gross_pnl - fee_per_trade
        gross += gross_pnl
        fees_paid += fee_per_trade
        trades += 1
        if net_pnl > 0:
            wins += 1

    net = gross - fees_paid
    win_rate = (wins / trades) if trades else 0.0
    return {
        "gross_profit": round(gross, 4),
        "fees_paid": round(fees_paid, 4),
        "net_profit": round(net, 4),
        "trades": trades,
        "tsl_hits": tsl_hits,
        "win_rate": round(win_rate, 4),
        "fee_taker_pct": fee.taker_pct,
    }


def simulate_buy_and_hold(
    df: pd.DataFrame,
    *,
    stake_usd: float,
    fee: ExchangeFeeSchedule,
) -> dict[str, Any] | None:
    if len(df) < 2:
        return None
    closes = df["close"].to_numpy(dtype=float)
    entry = float(closes[0])
    exit_p = float(closes[-1])
    if entry <= 0:
        return None
    gross_pnl = stake_usd * ((exit_p / entry) - 1.0)
    fee_paid = fee.round_trip_taker_cost(stake_usd)
    net = gross_pnl - fee_paid
    return {
        "strategy_id": "BUY_AND_HOLD",
        "timeframe": "ALL",
        "gross_profit": round(gross_pnl, 4),
        "fees_paid": round(fee_paid, 4),
        "net_profit": round(net, 4),
        "trades": 1,
        "tsl_hits": 0,
        "win_rate": 1.0 if net > 0 else 0.0,
        "fee_taker_pct": fee.taker_pct,
        "params": {},
        "trailing_stop_pct": 0.0,
        "phase": "baseline",
        "bar_count": len(df),
    }
