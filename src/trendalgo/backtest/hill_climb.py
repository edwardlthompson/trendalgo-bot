"""Deepen: params ±10 at signal-only (TSL=0) → TSL grid 1–20% (keep signal if better)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pandas as pd

from trendalgo.backtest.fleet_config import PASS12_TRAILING_STOP_PCT
from trendalgo.backtest.hill_climb_axes import int_params, seed_params
from trendalgo.backtest.hill_climb_brute import brute_pm_axes
from trendalgo.backtest.hill_climb_tsl import DEEPEN_TSL_PCTS, climb_tsl_grid
from trendalgo.backtest.sim_accel import accel_backend
from trendalgo.backtest.ta_fleet import backtest_one, default_params
from trendalgo.exchanges.fees import ExchangeFeeSchedule

ProgressFn = Callable[[str], None]
# Discovery / params use signal exits only (same as fleet pass 1–2).
SIGNAL_TSL = float(PASS12_TRAILING_STOP_PCT)
# Lowest trail considered when Stage D applies a real trailing stop.
MIN_TSL = 0.01

__all__ = ["DEEPEN_TSL_PCTS", "MIN_TSL", "SIGNAL_TSL", "climb_seed"]


def climb_seed(
    frame: pd.DataFrame,
    seed: dict[str, Any],
    *,
    fee: ExchangeFeeSchedule,
    stake_usd: float,
    timeframe: str,
    frames_by_tf: dict[str, pd.DataFrame] | None = None,
    on_progress: ProgressFn | None = None,
) -> dict[str, Any] | None:
    """Params ±10 at TSL=0 on the seed TF, then TSL 1–20%. Keeps signal-only if better."""
    del frames_by_tf  # Stage B already chose TF; no TF re-sweep under a trail.
    sid = str(seed.get("strategy_id") or "")
    if not sid:
        return None
    defaults = seed_params(sid, default_params(sid))
    params = seed_params(sid, seed.get("params") if isinstance(seed.get("params"), dict) else None)
    active_tf = str(seed.get("timeframe") or timeframe)
    active = frame

    best = _trial(active, sid, defaults, SIGNAL_TSL, fee=fee, stake=stake_usd, tf=active_tf)
    if best is None:
        best = {
            **seed,
            "params": defaults,
            "trailing_stop_pct": SIGNAL_TSL,
            "timeframe": active_tf,
        }
    best_net = float(best.get("net_profit") or float("-inf"))

    center = dict(defaults)
    if isinstance(best.get("params"), dict) and best.get("params"):
        center = seed_params(
            sid, best.get("params") if isinstance(best.get("params"), dict) else None
        )
    for key, value in params.items():
        center.setdefault(key, value)

    if on_progress is not None:
        on_progress(f"Deepening {sid} · params @ signal-only")
    params, best, best_net = brute_pm_axes(
        active,
        sid,
        center,
        tsl=SIGNAL_TSL,
        fee=fee,
        stake=stake_usd,
        tf=active_tf,
        best=best,
        best_net=best_net,
        trial_fn=_trial,
        on_progress=on_progress,
        radius=10,
    )
    # Stage D: trails only win when they beat this signal-only baseline.
    signal_net = best_net

    if on_progress is not None:
        on_progress(f"Deepening {sid} · TSL (accel={accel_backend()})")
    best = climb_tsl_grid(
        active, sid, params, active_tf, fee, stake_usd, best, best_net, trial_fn=_trial
    )

    if best is None:
        return None
    best["params"] = int_params(dict(best.get("params") or params), sid)
    best["timeframe"] = str(best.get("timeframe") or active_tf)
    return {
        **best,
        "optimized": True,
        "signal_net_profit": seed.get("net_profit", signal_net),
        "baseline_net_profit": seed.get("net_profit"),
        "baseline_params": seed.get("params"),
    }


def _trial(
    frame: pd.DataFrame,
    sid: str,
    params: dict[str, Any],
    tsl: float,
    *,
    fee: ExchangeFeeSchedule,
    stake: float,
    tf: str,
) -> dict[str, Any] | None:
    trial, _reason = backtest_one(
        frame,
        sid,
        fee,
        stake,
        timeframe=tf,
        lookback_seconds=0,
        params=params,
        trailing_stop_pct=max(0.0, float(tsl)),
        phase="optimize",
    )
    return trial
