"""Secret Sauce Final — vote helpers (≥2 agree ±1 bar) or best-holdout; exit+TSL search."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from trendalgo.backtest.secret_sauce_dossier import HeartbeatDossier, dossier_from_dict
from trendalgo.backtest.secret_sauce_features import entries_for_secret_sauce
from trendalgo.backtest.secret_sauce_lab.families import seeds_for_weights
from trendalgo.backtest.secret_sauce_lab.narrative import build_narrative
from trendalgo.backtest.secret_sauce_lab.regime_snapshot import detect_regime
from trendalgo.backtest.secret_sauce_lab.search import bh_net_profit, search_best_pair
from trendalgo.backtest.secret_sauce_lab.search_folds import bar_folds
from trendalgo.backtest.secret_sauce_lab.session_mask import apply_session_to_entries
from trendalgo.exchanges.fees import ExchangeFeeSchedule

_SID = "GEN_SECRET_1"


def cook_final_boss(
    df: pd.DataFrame,
    helper_rows: list[dict[str, Any]],
    *,
    fee: ExchangeFeeSchedule,
    stake_usd: float,
    oracle_swing_count: int = 0,
) -> tuple[HeartbeatDossier, Any, float, list[str]] | None:
    """Return (dossier, regime, tsl, voter_names) or None."""
    if df.empty or len(df) < 8:
        return None
    dossiers: list[tuple[str, HeartbeatDossier]] = []
    for row in helper_rows:
        name = str(row.get("indicator") or "")
        d = dossier_from_dict(row.get("heartbeat_dossier"))
        if d is None or bool(row.get("ss_lab_pending")) or bool(row.get("ss_unavailable")):
            continue
        dossiers.append((name, d))
    if not dossiers:
        return None
    n = len(df)
    masks = [
        (name, apply_session_to_entries(entries_for_secret_sauce(df, d.rule), df))
        for name, d in dossiers
    ]
    # Vote: bars where ≥2 helpers fire within ±1 (N — session soft-mask already applied).
    vote = np.zeros(n, dtype=bool)
    voters_at: list[list[str]] = [[] for _ in range(n)]
    for name, mask in masks:
        for i in range(n):
            if not mask[i]:
                continue
            for j in range(max(0, i - 1), min(n, i + 2)):
                if name not in voters_at[j]:
                    voters_at[j].append(name)
    for i in range(n):
        if len(voters_at[i]) >= 2:
            vote[i] = True
    # Fallback: best holdout helper entry alone (K).
    if not vote.any():
        best = max(
            dossiers,
            key=lambda nd: float(
                nd[1].holdout_net
                if nd[1].holdout_net is not None
                else nd[1].train_net or float("-inf")
            ),
        )
        vote = apply_session_to_entries(entries_for_secret_sauce(df, best[1].rule), df)
        voter_names = [best[0]]
        seed_entry = best[1].rule
    else:
        voter_names = sorted({v for vs in voters_at for v in vs if vs})
        voted = [nd for nd in dossiers if nd[0] in voter_names]
        seed_entry = max(
            voted,
            key=lambda nd: float(
                nd[1].holdout_net if nd[1].holdout_net is not None else float("-inf")
            ),
        )[1].rule
        voter_names = [nd[0] for nd in voted]
    del vote  # vote informs voter selection; entry search uses seed_entry conjuncts

    regime = detect_regime(df)
    bh = bh_net_profit(df, fee=fee, stake=stake_usd)
    fam = seeds_for_weights(_SID, {"adaptive_exit": 1.0}, volume_ok=regime.volume_ok)
    pairs = [(seed_entry, xr, "final_exit") for _e, xr, _f in fam]
    train, hold = bar_folds(len(df), holdout_frac=0.35, purge_bars=4)
    hit = search_best_pair(
        df,
        pairs,
        fee=fee,
        stake_usd=stake_usd,
        bh_net=bh,
        time_budget_s=None,
        train_indexes=train,
        holdout_indexes=hold,
        oracle_swing_count=oracle_swing_count,
    )
    if hit is None:
        # Ship seed entry + first family exit as last resort.
        if not fam:
            return None
        er, xr = seed_entry, fam[0][1]
        tsl = 0.0
        family = "final_fallback"
        train_n = hold_n = None
        gate = None
    else:
        er, xr, tsl = hit.entry, hit.exit, float(hit.trailing_stop_pct)
        family = hit.family
        train_n, hold_n, gate = hit.train_net, hit.holdout_net, hit.holdout_gate_ok
    formula, anti = build_narrative(
        regime,
        family=family,
        entry=er,
        exit_rule=xr,
        beat_bh=bh is not None and (hit.net if hit else 0) > (bh or 0),
    )
    anti += f" Final Boss voters: {', '.join(voter_names) or '—'}."
    dossier = HeartbeatDossier(
        rule=er,
        exit_rule=xr,
        formula_en=formula,
        train_coverage=0.0,
        holdout_coverage=0.0,
        swing_hits=tuple(),
        exit_hits=tuple(),
        oracle_entry_indexes=tuple(),
        oracle_exit_indexes=tuple(),
        anti_cheat=anti,
        holdout_gate_ok=gate,
        train_net=train_n,
        holdout_net=hold_n,
        trailing_stop_pct=tsl,
        residual_feature_hits=({"features": ["final_voters"], "voters": voter_names},),
    )
    return dossier, regime, tsl, voter_names
