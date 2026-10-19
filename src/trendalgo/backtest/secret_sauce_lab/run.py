"""Secret Sauce Lab entrypoint — regime budgets + fee-aware family search."""

from __future__ import annotations

from typing import Any

import pandas as pd

from trendalgo.backtest.secret_sauce_dossier import HeartbeatDossier
from trendalgo.backtest.secret_sauce_features import entries_for_secret_sauce
from trendalgo.backtest.secret_sauce_lab.families import seeds_for_weights
from trendalgo.backtest.secret_sauce_lab.narrative import build_narrative
from trendalgo.backtest.secret_sauce_lab.regime_snapshot import RegimeSnapshot, detect_regime
from trendalgo.backtest.secret_sauce_lab.search import bh_net_profit, search_best_pair
from trendalgo.backtest.ta_fleet import backtest_one
from trendalgo.exchanges.fees import ExchangeFeeSchedule

_SECRET_ID = "GEN_SECRET_1"
_HOLDOUT_FRAC = 0.35


def run_secret_sauce_lab(
    df: pd.DataFrame,
    *,
    fee: ExchangeFeeSchedule,
    stake_usd: float,
    oracle_trades: list[dict[str, Any]],
    bh_net: float | None = None,
    strategy_id: str = _SECRET_ID,
    time_budget_s: float = 4.0,
) -> tuple[HeartbeatDossier, RegimeSnapshot] | None:
    """Mine dossier via Lab; returns (dossier, regime) or None."""
    if df.empty or len(oracle_trades) < 2:
        return None
    regime = detect_regime(df)
    if bh_net is None:
        bh_net = bh_net_profit(df, fee=fee, stake=stake_usd)
    from trendalgo.backtest.secret_sauce_lab.pattern_mine import (
        indexes_from_trades,
        pattern_seed_pairs,
    )

    entries0, exits0 = indexes_from_trades(oracle_trades, n=len(df))
    pattern = pattern_seed_pairs(
        df,
        entry_indexes=entries0,
        exit_indexes=exits0,
        strategy_id=strategy_id,
        family="oracle_pattern",
        fee=fee,
        stake_usd=stake_usd,
        time_budget_s=min(1.2, time_budget_s * 0.25),
    )
    family_pairs = seeds_for_weights(strategy_id, regime.family_weights, volume_ok=regime.volume_ok)
    pairs = pattern + family_pairs
    picked = search_best_pair(
        df,
        pairs,
        fee=fee,
        stake_usd=stake_usd,
        bh_net=bh_net,
        time_budget_s=time_budget_s,
        direction=regime.direction,
    )
    if picked is None:
        return None
    entry_rule, exit_rule, search_net, family = picked
    formula, anti = build_narrative(
        regime,
        family=family,
        entry=entry_rule,
        exit_rule=exit_rule,
        beat_bh=bh_net is not None and search_net > bh_net,
    )
    entries = [
        int(t.get("entry_index") or -1)
        for t in oracle_trades
        if 0 <= int(t.get("entry_index") or -1) < len(df)
    ]
    exits = [
        int(t.get("exit_index") or -1)
        for t in oracle_trades
        if 0 <= int(t.get("exit_index") or -1) < len(df)
    ]
    entry_mask = entries_for_secret_sauce(df, entry_rule)
    exit_mask = entries_for_secret_sauce(df, exit_rule)
    if not entry_mask.any():
        return None
    train_e, hold_e = _split(entries)
    train_x, hold_x = _split(exits)
    train_cov = (_coverage(entry_mask, train_e) + _coverage(exit_mask, train_x)) / 2.0
    hold_cov = (_coverage(entry_mask, hold_e) + _coverage(exit_mask, hold_x)) / 2.0
    dossier = HeartbeatDossier(
        rule=entry_rule,
        exit_rule=exit_rule,
        formula_en=formula,
        train_coverage=max(train_cov, 0.0),
        holdout_coverage=max(hold_cov, 0.0),
        swing_hits=tuple(bool(entry_mask[i]) for i in entries),
        exit_hits=tuple(bool(exit_mask[i]) for i in exits),
        oracle_entry_indexes=tuple(entries),
        oracle_exit_indexes=tuple(exits),
        anti_cheat=anti,
    )
    return dossier, regime


def eval_lab_trial(
    df: pd.DataFrame,
    dossier: HeartbeatDossier,
    *,
    fee: ExchangeFeeSchedule,
    stake_usd: float,
    timeframe: str = "1h",
) -> dict[str, Any] | None:
    trial, _reason = backtest_one(
        df,
        dossier.rule.strategy_id,
        fee,
        stake_usd,
        timeframe=timeframe,
        lookback_seconds=0,
        params=dossier.eval_params(),
        phase="secret_sauce",
    )
    return dict(trial) if trial is not None else None


def _split(indexes: list[int]) -> tuple[list[int], list[int]]:
    if not indexes:
        return [], []
    split = max(1, int(len(indexes) * (1.0 - _HOLDOUT_FRAC)))
    train_idx, hold_idx = indexes[:split], indexes[split:]
    if not hold_idx:
        hold_idx = indexes[-1:]
        train_idx = indexes[:-1] or indexes
    return train_idx, hold_idx


def _coverage(mask: Any, indexes: list[int]) -> float:
    if not indexes:
        return 0.0
    return sum(1 for i in indexes if mask[i]) / float(len(indexes))
