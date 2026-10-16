"""TSL grid climb with signal reuse + accel backend."""

from __future__ import annotations

from typing import Any

import pandas as pd

from trendalgo.backtest.sim_accel import simulate_tsl_grid
from trendalgo.backtest.ta_fleet import prepare_signals, row_from_stats
from trendalgo.exchanges.fees import ExchangeFeeSchedule

DEEPEN_TSL_PCTS: tuple[float, ...] = tuple(i / 100.0 for i in range(1, 21))


def climb_tsl_grid(
    frame: pd.DataFrame,
    sid: str,
    params: dict[str, Any],
    tf: str,
    fee: ExchangeFeeSchedule,
    stake: float,
    best: dict[str, Any],
    best_net: float,
    *,
    trial_fn: Any,
) -> dict[str, Any]:
    """Reuse signals across DEEPEN_TSL_PCTS; fall back to trial_fn per TSL."""
    prepared = prepare_signals(frame, sid, params)
    entries, exits, used = prepared
    if entries is None or exits is None or not isinstance(used, dict):
        for tsl in DEEPEN_TSL_PCTS:
            trial = trial_fn(frame, sid, params, tsl, fee=fee, stake=stake, tf=tf)
            if trial is None:
                continue
            net = float(trial.get("net_profit") or float("-inf"))
            if net > best_net:
                best, best_net = trial, net
        return best
    closes = frame["close"].to_numpy(dtype=float)
    for stats in simulate_tsl_grid(
        closes, entries, exits, DEEPEN_TSL_PCTS, stake_usd=stake, fee=fee
    ):
        if int(stats.get("trades") or 0) == 0:
            continue
        trial = row_from_stats(
            stats,
            strategy_id=sid,
            timeframe=tf,
            lookback_seconds=0,
            params=used,
            phase="optimize",
            bar_count=len(frame),
        )
        net = float(trial.get("net_profit") or float("-inf"))
        if net > best_net:
            best, best_net = trial, net
    return best
