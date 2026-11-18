"""P — distill sparse rule toward tradable Oracle proxy (next-bar closes), not HL indexes."""

from __future__ import annotations

from typing import Any

import pandas as pd

from trendalgo.backtest.secret_sauce_dossier import HeartbeatDossier
from trendalgo.backtest.secret_sauce_lab.narrative import build_narrative
from trendalgo.backtest.secret_sauce_lab.pattern_mine import pattern_seed_pairs
from trendalgo.backtest.secret_sauce_lab.regime_snapshot import detect_regime
from trendalgo.backtest.secret_sauce_lab.search import bh_net_profit, search_best_pair
from trendalgo.backtest.secret_sauce_lab.search_folds import bar_folds
from trendalgo.backtest.ta_simulator import simulate_oracle_tradable_proxy
from trendalgo.exchanges.fees import ExchangeFeeSchedule

_SID = "GEN_SECRET_1"


def cook_teacher_distill(
    df: pd.DataFrame,
    oracle_swings: list[dict[str, Any]],
    *,
    fee: ExchangeFeeSchedule,
    stake_usd: float,
) -> tuple[HeartbeatDossier, Any, float] | None:
    if df.empty or len(oracle_swings) < 2:
        return None
    proxy = simulate_oracle_tradable_proxy(df, oracle_swings, stake_usd=stake_usd, fee=fee)
    if proxy is None:
        return None
    # Use swing indexes as labels (timestamps already on swings) — same as pattern mine,
    # but objective is fee Net toward proxy path via search_best_pair.
    entries = [
        int(t["entry_index"])
        for t in oracle_swings
        if 0 <= int(t.get("entry_index") or -1) < len(df)
    ]
    exits = [
        int(t["exit_index"]) for t in oracle_swings if 0 <= int(t.get("exit_index") or -1) < len(df)
    ]
    seeds = pattern_seed_pairs(
        df,
        entry_indexes=entries,
        exit_indexes=exits,
        strategy_id=_SID,
        family="teacher_distill",
        fee=fee,
        stake_usd=stake_usd,
    )
    if not seeds:
        return None
    regime = detect_regime(df)
    bh = bh_net_profit(df, fee=fee, stake=stake_usd)
    train, hold = bar_folds(len(df), holdout_frac=0.35, purge_bars=4)
    hit = search_best_pair(
        df,
        seeds,
        fee=fee,
        stake_usd=stake_usd,
        bh_net=bh,
        time_budget_s=None,
        train_indexes=train,
        holdout_indexes=hold,
        oracle_swing_count=len(oracle_swings),
    )
    if hit is None:
        return None
    formula, anti = build_narrative(
        regime,
        family="teacher_distill",
        entry=hit.entry,
        exit_rule=hit.exit,
        beat_bh=bh is not None and hit.net > bh,
    )
    anti += " Teacher distill: imitate tradable Oracle proxy (next-bar closes), not HL indexes."
    dossier = HeartbeatDossier(
        rule=hit.entry,
        exit_rule=hit.exit,
        formula_en=formula,
        train_coverage=0.0,
        holdout_coverage=0.0,
        swing_hits=tuple(),
        exit_hits=tuple(),
        oracle_entry_indexes=tuple(entries),
        oracle_exit_indexes=tuple(exits),
        anti_cheat=anti,
        holdout_gate_ok=hit.holdout_gate_ok,
        train_net=hit.train_net,
        holdout_net=hit.holdout_net,
        trailing_stop_pct=float(hit.trailing_stop_pct),
        oracle_gap_net_pct=float(proxy.get("net_profit") or 0.0) - float(hit.net),
    )
    return dossier, regime, float(hit.trailing_stop_pct)
