"""Helper C — seed entry from Sauce TA / Peer; heavy adaptive exit search."""

from __future__ import annotations

from typing import Any

import pandas as pd

from trendalgo.backtest.oracle_pattern_mine import CompositeRule
from trendalgo.backtest.secret_sauce_dossier import HeartbeatDossier, dossier_from_dict
from trendalgo.backtest.secret_sauce_lab.families import seeds_for_weights
from trendalgo.backtest.secret_sauce_lab.narrative import build_narrative
from trendalgo.backtest.secret_sauce_lab.regime_snapshot import detect_regime
from trendalgo.backtest.secret_sauce_lab.search import bh_net_profit, search_best_pair
from trendalgo.backtest.secret_sauce_lab.search_folds import bar_folds
from trendalgo.exchanges.fees import ExchangeFeeSchedule

_SID = "GEN_SECRET_1"


def cook_exit_helper(
    df: pd.DataFrame,
    *,
    fee: ExchangeFeeSchedule,
    stake_usd: float,
    sauce_ta_row: dict[str, Any] | None = None,
    peer_row: dict[str, Any] | None = None,
    oracle_swing_count: int = 0,
) -> tuple[HeartbeatDossier, Any, float] | None:
    if df.empty or len(df) < 8:
        return None
    seed_entry: CompositeRule | None = None
    for row in (sauce_ta_row, peer_row):
        if not isinstance(row, dict):
            continue
        d = dossier_from_dict(row.get("heartbeat_dossier"))
        if d is not None:
            seed_entry = d.rule
            break
    regime = detect_regime(df)
    bh = bh_net_profit(df, fee=fee, stake=stake_usd)
    fam = seeds_for_weights(_SID, {"adaptive_exit": 1.0}, volume_ok=regime.volume_ok)
    pairs: list[tuple[Any, Any, str]] = []
    if seed_entry is not None:
        for _e, xr, _f in fam:
            pairs.append((seed_entry, xr, "exit_handoff"))
    pairs.extend((er, xr, "adaptive_exit") for er, xr, _f in fam)
    if not pairs:
        return None
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
        return None
    formula, anti = build_narrative(
        regime,
        family="adaptive_exit",
        entry=hit.entry,
        exit_rule=hit.exit,
        beat_bh=bh is not None and hit.net > bh,
    )
    anti += " Exit helper: entry seeded from Sauce TA/Peer when present; exits searched hard."
    dossier = HeartbeatDossier(
        rule=hit.entry,
        exit_rule=hit.exit,
        formula_en=formula,
        train_coverage=0.0,
        holdout_coverage=0.0,
        swing_hits=tuple(),
        exit_hits=tuple(),
        oracle_entry_indexes=tuple(),
        oracle_exit_indexes=tuple(),
        anti_cheat=anti,
        holdout_gate_ok=hit.holdout_gate_ok,
        train_net=hit.train_net,
        holdout_net=hit.holdout_net,
        trailing_stop_pct=float(hit.trailing_stop_pct),
    )
    return dossier, regime, float(hit.trailing_stop_pct)
