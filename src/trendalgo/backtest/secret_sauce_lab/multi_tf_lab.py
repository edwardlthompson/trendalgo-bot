"""Multi-TF first-pass Lab — keep best fee Net % (timestamp-remap swings across TFs)."""

from __future__ import annotations

from typing import Any

import pandas as pd

from trendalgo.backtest.secret_sauce_dossier import HeartbeatDossier
from trendalgo.backtest.secret_sauce_lab.regime_snapshot import RegimeSnapshot
from trendalgo.backtest.secret_sauce_lab.run import eval_lab_trial, run_secret_sauce_lab
from trendalgo.backtest.secret_sauce_lab.search import lab_time_budget_s
from trendalgo.exchanges.fees import ExchangeFeeSchedule

_DENSE = ("1h", "2h", "3h", "4h", "8h")
_MIN_EXTRA_BARS = 50  # extra TFs need enough bars; Oracle TF always tried
_MAX_TFS = 5


def mine_best_across_tfs(
    frames_by_tf: dict[str, Any],
    *,
    oracle_tf: str,
    oracle_trades: list[dict[str, Any]],
    fee: ExchangeFeeSchedule,
    stake_usd: float,
    time_budget_s: float | None = None,
    peer_net: float | None = None,
) -> tuple[HeartbeatDossier, RegimeSnapshot, dict[str, Any], str] | None:
    """Run Lab on Oracle TF + densest frames; keep max fee Net % trial."""
    tfs = _candidate_tfs(frames_by_tf, oracle_tf)
    if not tfs:
        return None
    n_swings = len(oracle_trades)
    # Uncapped: each TF gets a full cook (no wall-clock split).
    per = float(time_budget_s) if time_budget_s is not None else lab_time_budget_s(n_swings)
    best: tuple[HeartbeatDossier, RegimeSnapshot, dict[str, Any], str] | None = None
    best_net = float("-inf")
    oracle_net_on_oracle_tf: float | None = None
    for tf in tfs:
        frame = frames_by_tf.get(tf)
        if frame is None or getattr(frame, "empty", True):
            continue
        trades = remap_oracle_trades(frame, oracle_trades, oracle_tf=oracle_tf, search_tf=tf)
        try:
            packed = run_secret_sauce_lab(
                frame,
                fee=fee,
                stake_usd=stake_usd,
                oracle_trades=trades,
                time_budget_s=per,
                peer_net=peer_net,
                require_peer_clear=False,
            )
        except (TypeError, ValueError, KeyError, IndexError):
            continue
        if packed is None:
            continue
        dossier, regime = packed
        trial = eval_lab_trial(frame, dossier, fee=fee, stake_usd=stake_usd, timeframe=tf)
        if trial is None:
            continue
        net = float(trial.get("net_profit") or 0.0)
        if tf == oracle_tf:
            oracle_net_on_oracle_tf = net
        # Prefer Oracle TF when within 5% relative of denser-TF winner (UX honesty).
        if best is None:
            best_net = net
            best = (dossier, regime, dict(trial), tf)
        elif net > best_net:
            if (
                best[3] == oracle_tf
                and oracle_net_on_oracle_tf is not None
                and best_net > 0
                and net < best_net * 1.05
            ):
                pass  # keep Oracle TF
            else:
                best_net = net
                best = (dossier, regime, dict(trial), tf)
        elif tf == oracle_tf and best[3] != oracle_tf and best_net > 0 and net >= best_net / 1.05:
            best_net = net
            best = (dossier, regime, dict(trial), tf)
    return best


def remap_oracle_trades(
    frame: pd.DataFrame,
    oracle_trades: list[dict[str, Any]],
    *,
    oracle_tf: str,
    search_tf: str,
) -> list[dict[str, Any]]:
    """Map Oracle swings onto ``frame`` by timestamp (never reuse raw indexes across TFs)."""
    n = len(frame)
    if search_tf == oracle_tf:
        valid = [
            t
            for t in oracle_trades
            if 0 <= int(t.get("entry_index") or -1) < n and 0 <= int(t.get("exit_index") or -1) < n
        ]
        if len(valid) >= 2:
            return valid
    remapped: list[dict[str, Any]] = []
    for trade in oracle_trades:
        entry_i = _resolve_bar(frame, trade.get("entry_time"), trade.get("entry_index"))
        exit_i = _resolve_bar(frame, trade.get("exit_time"), trade.get("exit_index"))
        if entry_i is None or exit_i is None or exit_i <= entry_i:
            continue
        item = dict(trade)
        item["entry_index"] = entry_i
        item["exit_index"] = exit_i
        remapped.append(item)
    if len(remapped) >= 2:
        return remapped
    # Coverage placeholders only — search scores fee P&L, not these indexes.
    a, b = max(10, n // 4), max(20, n // 2)
    return [
        {"entry_index": min(a, n - 6), "exit_index": min(a + 4, n - 2)},
        {"entry_index": min(b, n - 6), "exit_index": min(b + 4, n - 2)},
    ]


def _candidate_tfs(frames_by_tf: dict[str, Any], oracle_tf: str) -> list[str]:
    out: list[str] = []
    o_frame = frames_by_tf.get(oracle_tf)
    if o_frame is not None and not getattr(o_frame, "empty", True):
        out.append(oracle_tf)
    for tf in _DENSE:
        if not tf or tf in out:
            continue
        frame = frames_by_tf.get(tf)
        if frame is None or getattr(frame, "empty", True) or len(frame) < _MIN_EXTRA_BARS:
            continue
        out.append(tf)
        if len(out) >= _MAX_TFS:
            break
    return out


def _resolve_bar(frame: pd.DataFrame, stamp: Any, stored: Any) -> int | None:
    if stamp is not None and stamp != "":
        try:
            ts = pd.Timestamp(stamp)
            if ts is not pd.NaT:
                if getattr(frame.index, "tz", None) is not None and ts.tzinfo is None:
                    ts = ts.tz_localize("UTC")
                elif getattr(frame.index, "tz", None) is None and ts.tzinfo is not None:
                    ts = ts.tz_localize(None)
                loc = frame.index.get_indexer([ts], method="nearest")
                if len(loc) and 0 <= int(loc[0]) < len(frame):
                    return int(loc[0])
        except (TypeError, ValueError, KeyError):
            pass
    try:
        idx = int(stored)
    except (TypeError, ValueError):
        return None
    if 0 <= idx < len(frame):
        return idx
    return None
