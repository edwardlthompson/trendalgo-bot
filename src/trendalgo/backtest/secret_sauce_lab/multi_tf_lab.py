"""Multi-TF first-pass Lab — keep best fee Net %."""

from __future__ import annotations

from typing import Any

import pandas as pd

from trendalgo.backtest.secret_sauce_dossier import HeartbeatDossier
from trendalgo.backtest.secret_sauce_lab.regime_snapshot import RegimeSnapshot
from trendalgo.backtest.secret_sauce_lab.run import eval_lab_trial, run_secret_sauce_lab
from trendalgo.exchanges.fees import ExchangeFeeSchedule

_DENSE = ("1h", "2h", "3h", "4h")
_MIN_EXTRA_BARS = 50  # extra TFs need enough bars; Oracle TF always tried
_MAX_TFS = 5


def mine_best_across_tfs(
    frames_by_tf: dict[str, Any],
    *,
    oracle_tf: str,
    oracle_trades: list[dict[str, Any]],
    fee: ExchangeFeeSchedule,
    stake_usd: float,
    time_budget_s: float = 4.0,
) -> tuple[HeartbeatDossier, RegimeSnapshot, dict[str, Any], str] | None:
    """Run Lab on Oracle TF + densest frames; keep max fee Net % trial."""
    tfs = _candidate_tfs(frames_by_tf, oracle_tf)
    if not tfs:
        return None
    per = max(0.6, time_budget_s / float(len(tfs)))
    best: tuple[HeartbeatDossier, RegimeSnapshot, dict[str, Any], str] | None = None
    best_net = float("-inf")
    for tf in tfs:
        frame = frames_by_tf.get(tf)
        if frame is None or getattr(frame, "empty", True):
            continue
        trades = _trades_for_frame(frame, oracle_trades, oracle_tf=oracle_tf, search_tf=tf)
        try:
            packed = run_secret_sauce_lab(
                frame,
                fee=fee,
                stake_usd=stake_usd,
                oracle_trades=trades,
                time_budget_s=per,
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
        if net > best_net:
            best_net = net
            best = (dossier, regime, dict(trial), tf)
    return best


def _candidate_tfs(frames_by_tf: dict[str, Any], oracle_tf: str) -> list[str]:
    out: list[str] = []
    # Always include Oracle TF when a frame exists (even short synth fixtures).
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


def _trades_for_frame(
    frame: pd.DataFrame,
    oracle_trades: list[dict[str, Any]],
    *,
    oracle_tf: str,
    search_tf: str,
) -> list[dict[str, Any]]:
    """Reuse Oracle swings on matching TF; else pseudo indexes for dossier coverage."""
    n = len(frame)
    if search_tf == oracle_tf:
        valid = [
            t
            for t in oracle_trades
            if 0 <= int(t.get("entry_index") or -1) < n and 0 <= int(t.get("exit_index") or -1) < n
        ]
        if len(valid) >= 2:
            return valid
    # Coverage placeholders only — search scores fee P&L, not these indexes.
    a, b = max(10, n // 4), max(20, n // 2)
    return [
        {"entry_index": min(a, n - 6), "exit_index": min(a + 4, n - 2)},
        {"entry_index": min(b, n - 6), "exit_index": min(b + 4, n - 2)},
    ]
