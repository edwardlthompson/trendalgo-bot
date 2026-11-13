"""Helper A — freeze mutated peer entry; search exits (fee-honest, no exact clone)."""

from __future__ import annotations

from typing import Any

import pandas as pd

from trendalgo.backtest.secret_sauce_dossier import HeartbeatDossier
from trendalgo.backtest.secret_sauce_lab.catalog_reseed import (
    inspire_cross_seeds,
    is_exact_peer_clone,
    peer_hints_from_rows,
)
from trendalgo.backtest.secret_sauce_lab.families import seeds_for_weights
from trendalgo.backtest.secret_sauce_lab.regime_snapshot import detect_regime
from trendalgo.backtest.secret_sauce_lab.search import bh_net_profit, search_best_pair
from trendalgo.backtest.secret_sauce_lab.search_folds import bar_folds
from trendalgo.exchanges.fees import ExchangeFeeSchedule

_SID = "GEN_SECRET_1"
_HOLDOUT_FRAC = 0.35
_PURGE = 4


def cook_peer_helper(
    df: pd.DataFrame,
    rows: list[dict[str, Any]],
    *,
    fee: ExchangeFeeSchedule,
    stake_usd: float,
    oracle_swing_count: int = 0,
) -> tuple[HeartbeatDossier, Any, float] | None:
    """Return (dossier, regime, trailing_stop_pct) or None."""
    if df.empty or len(df) < 8:
        return None
    hints = peer_hints_from_rows(rows, preferred_tf="", prefer_osc=True)
    if not hints:
        hints = peer_hints_from_rows(rows, preferred_tf="", prefer_osc=True, require_beat_bh=False)
    if not hints:
        return None
    regime = detect_regime(df)
    bh = bh_net_profit(df, fee=fee, stake=stake_usd)
    entry_seeds = inspire_cross_seeds(_SID, hints[:3])
    # Pair each peer entry with adaptive-style exit diversity from family seeds.
    fam = seeds_for_weights(_SID, {"adaptive_exit": 1.0}, volume_ok=regime.volume_ok)
    pairs: list[tuple[Any, Any, str]] = []
    for er, xr, _fam_name in entry_seeds:
        pairs.append((er, xr, "peer_entry"))
        for _fe, fx, _ff in fam[:8]:
            pairs.append((er, fx, "peer_entry_exit"))
    if not pairs:
        return None
    train, hold = bar_folds(len(df), holdout_frac=_HOLDOUT_FRAC, purge_bars=_PURGE)
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
        require_peer_clear=False,
    )
    if hit is None or is_exact_peer_clone(hit.entry, hit.exit, hints):
        return None
    from trendalgo.backtest.secret_sauce_features import entries_for_secret_sauce
    from trendalgo.backtest.secret_sauce_lab.narrative import build_narrative

    formula, anti = build_narrative(
        regime,
        family=hit.family,
        entry=hit.entry,
        exit_rule=hit.exit,
        beat_bh=bh is not None and hit.net > bh,
    )
    anti += " Peer-entry helper: mutated peer levels; exits searched; not a catalog clone."
    em = entries_for_secret_sauce(df, hit.entry)
    dossier = HeartbeatDossier(
        rule=hit.entry,
        exit_rule=hit.exit,
        formula_en=formula,
        train_coverage=0.0,
        holdout_coverage=0.0,
        holdout_fit_coverage=0.0,
        holdout_gate_ok=hit.holdout_gate_ok,
        train_net=hit.train_net,
        holdout_net=hit.holdout_net,
        swing_hits=tuple(),
        exit_hits=tuple(),
        oracle_entry_indexes=tuple(),
        oracle_exit_indexes=tuple(),
        anti_cheat=anti,
        trailing_stop_pct=float(hit.trailing_stop_pct),
    )
    del em
    return dossier, regime, float(hit.trailing_stop_pct)
