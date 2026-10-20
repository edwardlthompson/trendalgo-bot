"""TSL grid climb with signal reuse + plateau pick (lowest safe + breath)."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from trendalgo.backtest.sim_accel import simulate_tsl_grid
from trendalgo.backtest.ta_fleet import prepare_signals, row_from_stats
from trendalgo.backtest.tsl_plateau import TSL_BREATH_PCT, pick_tsl_from_grid
from trendalgo.exchanges.fees import ExchangeFeeSchedule

DEEPEN_TSL_PCTS: tuple[float, ...] = tuple(i / 100.0 for i in range(1, 21))

__all__ = [
    "DEEPEN_TSL_PCTS",
    "TSL_BREATH_PCT",
    "assign_protective_tsl_from_masks",
    "climb_tsl_grid",
    "pick_tsl_from_grid",
]


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
    """Simulate DEEPEN_TSL_PCTS once, then plateau-pick a protective TSL > 0."""
    signal_net = float(best_net)
    trials = _collect_grid_trials(frame, sid, params, tf, fee, stake, trial_fn=trial_fn)
    picked = pick_tsl_from_grid(trials, signal_net=signal_net)
    if picked is not None:
        return picked
    if float(best.get("trailing_stop_pct") or 0.0) <= 0 and trials:
        fallback = max(
            (t for t in trials if float(t.get("trailing_stop_pct") or 0) > 0),
            key=lambda r: float(r.get("net_profit") or float("-inf")),
            default=None,
        )
        if fallback is not None:
            return fallback
    return best


def assign_protective_tsl_from_masks(
    frame: pd.DataFrame,
    entries: np.ndarray,
    exits: np.ndarray,
    *,
    fee: ExchangeFeeSchedule,
    stake: float,
    signal_net: float | None = None,
    base: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Grid-pick a TSL for precomputed entry/exit masks (Sauce / undepened)."""
    closes = frame["close"].to_numpy(dtype=float)
    trials: list[dict[str, Any]] = []
    for stats in simulate_tsl_grid(
        closes, entries, exits, DEEPEN_TSL_PCTS, stake_usd=stake, fee=fee
    ):
        if int(stats.get("trades") or 0) < 1:
            continue
        row = dict(base or {})
        row.update(stats)
        row["trailing_stop_pct"] = float(stats.get("trailing_stop_pct") or 0.0)
        trials.append(row)
    return pick_tsl_from_grid(trials, signal_net=signal_net)


def _collect_grid_trials(
    frame: pd.DataFrame,
    sid: str,
    params: dict[str, Any],
    tf: str,
    fee: ExchangeFeeSchedule,
    stake: float,
    *,
    trial_fn: Any,
) -> list[dict[str, Any]]:
    prepared = prepare_signals(frame, sid, params)
    entries, exits, used = prepared
    trials: list[dict[str, Any]] = []
    if entries is None or exits is None or not isinstance(used, dict):
        for tsl in DEEPEN_TSL_PCTS:
            trial = trial_fn(frame, sid, params, tsl, fee=fee, stake=stake, tf=tf)
            if trial is None or int(trial.get("trades") or 0) < 1:
                continue
            row = dict(trial)
            row["trailing_stop_pct"] = float(tsl)
            trials.append(row)
        return trials
    closes = frame["close"].to_numpy(dtype=float)
    for stats in simulate_tsl_grid(
        closes, entries, exits, DEEPEN_TSL_PCTS, stake_usd=stake, fee=fee
    ):
        if int(stats.get("trades") or 0) == 0:
            continue
        trials.append(
            row_from_stats(
                stats,
                strategy_id=sid,
                timeframe=tf,
                lookback_seconds=0,
                params=used,
                phase="optimize",
                bar_count=len(frame),
            )
        )
    return trials
