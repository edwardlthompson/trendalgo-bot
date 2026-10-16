"""TF defaults sweep + ±10 integer brute-force per axis (no hill-climb)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pandas as pd

from trendalgo.backtest.heartbeat_tf import HEARTBEAT_TIMEFRAMES, sort_timeframes
from trendalgo.backtest.hill_climb_axes import climb_axes
from trendalgo.exchanges.fees import ExchangeFeeSchedule

ProgressFn = Callable[[str], None]
TrialFn = Callable[..., dict[str, Any] | None]
PM10 = 10
# Back-compat alias for older tests / imports.
PM5 = PM10


def brute_tf_defaults(
    frames: dict[str, pd.DataFrame],
    sid: str,
    params: dict[str, Any],
    *,
    tsl: float,
    fee: ExchangeFeeSchedule,
    stake: float,
    best: dict[str, Any],
    best_net: float,
    trial_fn: TrialFn,
    on_progress: ProgressFn | None = None,
) -> tuple[str, pd.DataFrame, dict[str, Any], float]:
    """Try every loaded heartbeat TF with default params; return best TF + frame."""
    if on_progress is not None:
        on_progress(f"Deepening {sid} · brute TF 1h–24h (defaults)")
    active_tf = str(best.get("timeframe") or next(iter(frames), "1h"))
    active = frames.get(active_tf)
    if active is None:
        active = next(iter(frames.values()))
        active_tf = next(iter(frames.keys()))
    ordered = sort_timeframes(tuple(frames.keys()) or HEARTBEAT_TIMEFRAMES)
    for label in ordered:
        frame = frames.get(label)
        if frame is None:
            continue
        trial = trial_fn(frame, sid, params, tsl, fee=fee, stake=stake, tf=label)
        if trial is None:
            continue
        net = float(trial.get("net_profit") or float("-inf"))
        if net > best_net:
            best, best_net, active_tf, active = trial, net, label, frame
    return active_tf, active, best, best_net


def brute_pm_axes(
    frame: pd.DataFrame,
    sid: str,
    params: dict[str, Any],
    *,
    tsl: float,
    fee: ExchangeFeeSchedule,
    stake: float,
    tf: str,
    best: dict[str, Any],
    best_net: float,
    trial_fn: TrialFn,
    on_progress: ProgressFn | None = None,
    radius: int = PM10,
) -> tuple[dict[str, Any], dict[str, Any], float]:
    """Try every integer in [cur−radius, cur+radius] ∩ bounds (coordinate descent)."""
    for key, _step, lo, hi, _as_int in climb_axes(sid, params):
        if on_progress is not None:
            on_progress(f"Deepening {sid} · brute {key} ±{radius}")
        raw = params.get(key)
        if raw is None:
            continue
        try:
            base = int(round(float(raw)))
        except (TypeError, ValueError):
            continue
        lo_i, hi_i = int(lo), int(hi)
        start = max(lo_i, base - radius)
        stop = min(hi_i, base + radius)
        for val in range(start, stop + 1):
            if val == params.get(key):
                continue
            trial_params = {**params, key: val}
            trial = trial_fn(frame, sid, trial_params, tsl, fee=fee, stake=stake, tf=tf)
            if trial is None:
                continue
            net = float(trial.get("net_profit") or float("-inf"))
            if net > best_net:
                best, best_net, params = trial, net, trial_params
    return params, best, best_net


# Alias used by older call sites / tests.
brute_pm5_axes = brute_pm_axes
