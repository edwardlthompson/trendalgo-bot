"""Timeframe ±1h walk for hill-climb (1h..24h)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pandas as pd

from trendalgo.backtest.heartbeat_tf import HEARTBEAT_TIMEFRAMES, timeframe_hours
from trendalgo.exchanges.fees import ExchangeFeeSchedule

ProgressFn = Callable[[str], None]
MAX_STEPS = 8
MIN_TSL = 0.01


def climb_timeframe(
    sid: str,
    params: dict[str, Any],
    *,
    frames: dict[str, pd.DataFrame],
    active_tf: str,
    best: dict[str, Any],
    best_net: float,
    fee: ExchangeFeeSchedule,
    stake: float,
    trial_fn: Callable[..., dict[str, Any] | None],
    on_progress: ProgressFn | None = None,
) -> tuple[dict[str, Any], float, str, pd.DataFrame]:
    hours = timeframe_hours(active_tf)
    if hours is None or not frames:
        return best, best_net, active_tf, frames[active_tf]
    if on_progress is not None:
        on_progress(f"Deepening {sid} · timeframe")
    cur_h, cur_tf = hours, active_tf
    for direction in (1, -1):
        steps = 0
        h = cur_h
        while steps < MAX_STEPS:
            steps += 1
            nxt_h = h + direction
            if nxt_h < 1 or nxt_h > 24:
                break
            label = f"{nxt_h}h"
            if label not in frames and label not in HEARTBEAT_TIMEFRAMES:
                break
            frame = frames.get(label)
            if frame is None:
                break
            trial = trial_fn(frame, sid, params, MIN_TSL, fee=fee, stake=stake, tf=label)
            if trial is None:
                break
            net = float(trial.get("net_profit") or float("-inf"))
            if net > best_net:
                best, best_net, h, cur_tf = trial, net, nxt_h, label
            else:
                break
    return best, best_net, cur_tf, frames[cur_tf]
