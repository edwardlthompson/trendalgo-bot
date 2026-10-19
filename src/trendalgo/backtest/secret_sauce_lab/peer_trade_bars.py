"""On-demand top-peer trade bars for pattern reverse-mine."""

from __future__ import annotations

from typing import Any

import pandas as pd

from trendalgo.backtest.secret_sauce_lab.families import seeds_for_weights
from trendalgo.backtest.secret_sauce_lab.pattern_mine import pattern_seed_pairs
from trendalgo.backtest.secret_sauce_lab.peer_inspire import inspire_seeds_for_hints
from trendalgo.backtest.ta_fleet import backtest_one

_SID = "GEN_SECRET_1"
_FAT = {
    "dip_uptrend": 1.0,
    "mean_reversion": 1.0,
    "osc_cross": 1.0,
    "momentum": 1.0,
    "squeeze_breakout": 0.5,
    "volume_impulse": 0.5,
}


def top_peer_row(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Absolute max Net % catalog peer (skip Oracle / B&H / Sauce)."""
    skip = {
        "Oracle max",
        "B&H",
        "Secret Sauce",
        "Secret Sauce TA",
        "Secret Sauce Lab",
    }
    best: dict[str, Any] | None = None
    best_net = float("-inf")
    for r in rows:
        name = str(r.get("indicator") or "")
        if name in skip:
            continue
        net = float(r.get("net_pct") or float("-inf"))
        if net > best_net:
            best_net = net
            best = r
    return best


def rsx_seed_from_peer(peer: dict[str, Any] | None) -> dict[str, Any] | None:
    """Build RSX neighborhood seed hint from absolute top peer row."""
    if peer is None:
        return None
    from trendalgo.backtest.secret_sauce_lab.catalog_reseed import is_rsx_like_hint

    raw_params = peer.get("params")
    raw: dict[str, Any] = dict(raw_params) if isinstance(raw_params, dict) else {}
    hint = {
        "indicator": str(peer.get("indicator") or ""),
        "kind": str(raw.get("kind") or ""),
        "entry_level": float(raw.get("entry_level") or 30),
        "exit_level": float(raw.get("exit_level") or 70),
        "period": int(raw.get("timeperiod") or raw.get("length") or 14),
        "net_pct": float(peer.get("net_pct") or 0.0),
    }
    return hint if is_rsx_like_hint(hint) else None


def peer_trade_indexes(
    df: pd.DataFrame,
    peer: dict[str, Any],
    *,
    fee: Any,
    stake: float,
) -> tuple[list[int], list[int]]:
    """Re-sim peer with collect_trades; map entry/exit times → bar indexes."""
    sid = str(peer.get("strategy_id") or peer.get("indicator") or "")
    if not sid or df is None or getattr(df, "empty", True):
        return [], []
    raw_params = peer.get("params")
    params: dict[str, Any] = dict(raw_params) if isinstance(raw_params, dict) else {}
    tsl = float(peer.get("trailing_stop_pct") or peer.get("trailing_stop_loss_pct") or 0.0)
    tf = str(peer.get("timeframe") or "1h")
    try:
        trial, _err = backtest_one(
            df,
            sid,
            fee,
            stake,
            timeframe=tf,
            lookback_seconds=0,
            params=params,
            trailing_stop_pct=tsl,
            collect_trades=True,
        )
    except (TypeError, ValueError, KeyError, IndexError):
        return [], []
    if trial is None:
        return [], []
    return _indexes_from_times(df, list(trial.get("trade_list") or []))


def pattern_and_inspire_seeds(
    search_frame: Any,
    search_tf: str,
    hints: list[dict[str, Any]],
    peer_row: dict[str, Any] | None,
    fee: Any,
    stake: float,
) -> list[tuple[Any, Any, str]]:
    """Peer-trade pattern seeds first, then peer-class inspire skim."""
    seeds: list[tuple[Any, Any, str]] = []
    if peer_row is not None and str(peer_row.get("timeframe") or "") in {"", search_tf}:
        e_idx, x_idx = peer_trade_indexes(search_frame, peer_row, fee=fee, stake=stake)
        if len(e_idx) >= 2 and len(x_idx) >= 1:
            seeds.extend(
                pattern_seed_pairs(
                    search_frame,
                    entry_indexes=e_idx,
                    exit_indexes=x_idx,
                    strategy_id=_SID,
                    family="peer_pattern",
                    fee=fee,
                    stake_usd=stake,
                    time_budget_s=0.9,
                )
            )
    if hints:
        seeds.extend(inspire_seeds_for_hints(_SID, hints))
    if not seeds:
        seeds = [
            (er, xr, "peer_fat") for er, xr, _f in seeds_for_weights(_SID, _FAT, volume_ok=True)
        ]
    return seeds


def _indexes_from_times(
    df: pd.DataFrame, trades: list[dict[str, Any]]
) -> tuple[list[int], list[int]]:
    entries: list[int] = []
    exits: list[int] = []
    for t in trades:
        if t.get("entry_index") is not None:
            ei = int(t["entry_index"])
            if 0 <= ei < len(df):
                entries.append(ei)
        if t.get("exit_index") is not None:
            xi = int(t["exit_index"])
            if 0 <= xi < len(df):
                exits.append(xi)
    if entries and exits:
        return entries, exits
    idx = df.index
    for t in trades:
        e_loc = _lookup(idx, t.get("entry_time"))
        x_loc = _lookup(idx, t.get("exit_time"))
        if e_loc is not None:
            entries.append(e_loc)
        if x_loc is not None:
            exits.append(x_loc)
    return entries, exits


def _lookup(index: Any, stamp: Any) -> int | None:
    if stamp is None:
        return None
    try:
        ts = pd.Timestamp(stamp)
        if getattr(index, "tz", None) is not None and ts.tzinfo is None:
            ts = ts.tz_localize("UTC")
        elif getattr(index, "tz", None) is None and ts.tzinfo is not None:
            ts = ts.tz_localize(None)
        loc = index.get_indexer([ts], method="nearest")
        if len(loc) and loc[0] >= 0:
            return int(loc[0])
    except (TypeError, ValueError, KeyError):
        return None
    return None
