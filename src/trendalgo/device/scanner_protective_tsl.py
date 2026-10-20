"""Stamp a grid-picked protective TSL onto Results rows that still have TSL=0."""

from __future__ import annotations

from typing import Any

import pandas as pd

from trendalgo.backtest.hill_climb_tsl import DEEPEN_TSL_PCTS
from trendalgo.backtest.ta_fleet import backtest_one
from trendalgo.backtest.tsl_plateau import pick_tsl_from_grid
from trendalgo.exchanges.fees import ExchangeFeeSchedule

_SKIP = frozenset({"B&H", "Oracle max"})


def stamp_lts_protective_tsl(
    row: dict[str, Any],
    frame: pd.DataFrame,
    *,
    fee: ExchangeFeeSchedule,
    stake: float,
) -> dict[str, Any]:
    """If Results TSL is 0/missing, grid-pick via backtest_one and rewrite percent fields."""
    name = str(row.get("indicator") or "").strip()
    if name in _SKIP or str(row.get("skip_reason") or "").strip():
        return row
    if bool(row.get("ss_lab_pending")):
        return row
    raw = row.get("trailing_stop_loss_pct")
    if raw is None:
        raw = row.get("trailing_stop_pct")
    try:
        if raw not in (None, "-", "") and float(raw) > 0:
            return row
    except (TypeError, ValueError):
        pass
    sid = str(row.get("strategy_id") or name or "").strip()
    if not sid:
        return row
    params = dict(row.get("params") or {}) if isinstance(row.get("params"), dict) else {}
    # Lab / Sauce store dossier bits under params; keep strategy_id for GEN_SECRET eval.
    if sid.upper().startswith("GEN_SECRET") and "strategy_id" not in params:
        params = {**params, "strategy_id": sid}
    # Repair RSI 30/70 incorrectly stamped onto WILLR/CTI/FISHER during deepen.
    from trendalgo.backtest.hill_climb_axes import int_params
    from trendalgo.ta.signal_kinds import signal_kind

    if signal_kind(sid) == "bounded_reversal":
        params = int_params(params, sid)
    tf = str(row.get("timeframe") or "1h")
    signal_net = _signal_net_usd(row, stake)
    trials: list[dict[str, Any]] = []
    for tsl in DEEPEN_TSL_PCTS:
        trial, _reason = backtest_one(
            frame,
            sid,
            fee,
            stake,
            timeframe=tf,
            lookback_seconds=0,
            params=params,
            trailing_stop_pct=float(tsl),
            phase="optimize",
        )
        if trial is None or int(trial.get("trades") or 0) < 1:
            continue
        row_t = dict(trial)
        row_t["trailing_stop_pct"] = float(tsl)
        trials.append(row_t)
    picked = pick_tsl_from_grid(trials, signal_net=signal_net)
    if picked is None:
        return row
    out = _apply_picked_to_lts(row, picked, stake=stake)
    # Persist repaired oscillator levels (not RSI 30/70 on WILLR/CTI).
    out["params"] = dict(params)
    return out


def stamp_rows_protective_tsl(
    rows: list[dict[str, Any]],
    frames_by_tf: dict[str, pd.DataFrame],
    *,
    fee: ExchangeFeeSchedule,
    stake: float,
) -> list[dict[str, Any]]:
    """Stamp every zero-TSL Results row that has a matching timeframe frame."""
    out: list[dict[str, Any]] = []
    for row in rows:
        tf = str(row.get("timeframe") or "")
        # Exact TF only — wrong-TF fallback yields empty masks and leaves TSL=0.
        frame = frames_by_tf.get(tf)
        if frame is None:
            out.append(row)
            continue
        out.append(stamp_lts_protective_tsl(row, frame, fee=fee, stake=stake))
    return out


def _signal_net_usd(row: dict[str, Any], stake: float) -> float | None:
    raw = row.get("signal_net_pct")
    if raw is None:
        raw = row.get("net_pct")
    try:
        if raw in (None, "-", ""):
            return None
        return float(raw) / 100.0 * float(stake)
    except (TypeError, ValueError):
        return None


def _apply_picked_to_lts(
    row: dict[str, Any],
    picked: dict[str, Any],
    *,
    stake: float,
) -> dict[str, Any]:
    out = dict(row)
    tsl_frac = float(picked.get("trailing_stop_pct") or 0.0)
    tsl_pct = tsl_frac * 100.0 if 0.0 < tsl_frac <= 1.0 else tsl_frac
    out["trailing_stop_pct"] = float(tsl_pct)
    out["trailing_stop_loss_pct"] = float(tsl_pct)
    out["tsl_hits"] = int(picked.get("tsl_hits") or 0)
    out["trades"] = int(picked.get("trades") or out.get("trades") or 0)
    out["wins"] = int(picked.get("wins") or out.get("wins") or 0)
    out["open_trades"] = int(picked.get("open_trades") or 0)
    try:
        net = float(picked.get("net_profit") or 0.0)
        out["net_pct"] = (net / stake) * 100.0 if stake else 0.0
    except (TypeError, ValueError):
        pass
    wr = picked.get("win_rate")
    if wr is not None:
        try:
            out["win_pct"] = float(wr) * 100.0
        except (TypeError, ValueError):
            pass
    if picked.get("protective_tsl"):
        out["protective_tsl"] = True
    if picked.get("tsl_breath"):
        out["tsl_breath"] = True
    return out
