"""Q — shallow genetic search over conjunct pairs (fee + holdout fitness)."""

from __future__ import annotations

import random
from typing import Any

from trendalgo.backtest.oracle_pattern_mine import CompositeRule, RuleConjunct
from trendalgo.backtest.secret_sauce_dossier import HeartbeatDossier
from trendalgo.backtest.secret_sauce_lab.families import seeds_for_weights
from trendalgo.backtest.secret_sauce_lab.narrative import build_narrative
from trendalgo.backtest.secret_sauce_lab.regime_snapshot import detect_regime
from trendalgo.backtest.secret_sauce_lab.search import bh_net_profit, search_best_pair
from trendalgo.backtest.secret_sauce_lab.search_folds import bar_folds
from trendalgo.backtest.secret_sauce_seeds import classic_pair_seeds
from trendalgo.exchanges.fees import ExchangeFeeSchedule

_SID = "GEN_SECRET_1"
_GENS = 4
_POP = 12


def cook_genetic(
    df: Any,
    *,
    fee: ExchangeFeeSchedule,
    stake_usd: float,
    oracle_swing_count: int = 0,
    rng: random.Random | None = None,
) -> tuple[HeartbeatDossier, Any, float] | None:
    rng = rng or random.Random(7)
    regime = detect_regime(df)
    base = seeds_for_weights(_SID, regime.family_weights, volume_ok=regime.volume_ok)
    base += [(er, xr, "classic") for er, xr in classic_pair_seeds(_SID)[:8]]
    if not base:
        return None
    pop = list(base[:_POP])
    for _ in range(_GENS):
        kids: list[tuple[Any, Any, str]] = []
        for er, xr, _fam in pop:
            if not er.conjuncts or not xr.conjuncts:
                continue
            # Mutate one entry conjunct value ±10%.
            c0 = er.conjuncts[0]
            scale = 1.0 + rng.uniform(-0.1, 0.1)
            mut = RuleConjunct(feature=c0.feature, op=c0.op, value=float(c0.value) * scale)
            ner = CompositeRule(
                strategy_id=_SID, conjuncts=(mut, *er.conjuncts[1:]), rationale="genetic"
            )
            kids.append((ner, xr, "genetic"))
        pop = pop + kids
        pop = pop[: _POP * 2]
    bh = bh_net_profit(df, fee=fee, stake=stake_usd)
    train, hold = bar_folds(len(df), holdout_frac=0.35, purge_bars=4)
    hit = search_best_pair(
        df,
        pop,
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
        family="genetic",
        entry=hit.entry,
        exit_rule=hit.exit,
        beat_bh=bh is not None and hit.net > bh,
    )
    anti += " Genetic shallow search: mutated conjunct values under fee+holdout fitness."
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
