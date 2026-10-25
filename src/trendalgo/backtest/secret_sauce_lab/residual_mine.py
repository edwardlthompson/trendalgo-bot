"""Phase 1a — residual conjunct search (AND with primary; fee-aware)."""

from __future__ import annotations

import time
from typing import Any

import pandas as pd

from trendalgo.backtest.oracle_pattern_mine import CompositeRule, RuleConjunct
from trendalgo.backtest.secret_sauce_features import feature_keys_for
from trendalgo.backtest.secret_sauce_lab.columnar import feature_matrix, mask_conjuncts
from trendalgo.backtest.secret_sauce_lab.label_rules import pick_rules_at_labels
from trendalgo.backtest.ta_simulator import simulate_long_with_fees
from trendalgo.exchanges.fees import ExchangeFeeSchedule

_MAX_ENTRY_FRAC = 0.55
_MAX_EXIT_FRAC = 0.80
_MAX_TRADES = 200
_FAMILY = "residual_and"


def try_residual_refine(
    df: pd.DataFrame,
    entry: CompositeRule,
    exit_rule: CompositeRule,
    baseline_net: float,
    *,
    residual_entries: tuple[int, ...],
    residual_exits: tuple[int, ...],
    fee: ExchangeFeeSchedule,
    stake_usd: float,
    time_budget_s: float = 0.8,
) -> tuple[CompositeRule, CompositeRule, float, str] | None:
    """AND one causal conjunct onto entry and/or exit to cover residual Oracle bars.

    Returns improved (entry, exit, net, family) or None if no fee-Net lift.
    OR is skipped: CompositeRule is AND-only and must re-sim identically.
    """
    if df.empty or stake_usd <= 0:
        return None
    if not residual_entries and not residual_exits:
        return None
    t0 = time.perf_counter()
    cols, feats = feature_matrix(df)
    if not feats or not cols:
        return None
    keys = feature_keys_for(df, include_pivots=True)
    n = len(df)
    best: tuple[CompositeRule, CompositeRule, float] | None = None

    entry_cands = _extra_conjuncts(
        feats,
        _expand(list(residual_entries), n),
        keys,
        strategy_id=entry.strategy_id,
        side="entry",
        existing=entry.conjuncts,
    )
    exit_cands = _extra_conjuncts(
        feats,
        _expand(list(residual_exits), n),
        keys,
        strategy_id=exit_rule.strategy_id,
        side="exit",
        existing=exit_rule.conjuncts,
    )

    # Prefer entry-side AND, then exit-side, then both (one each).
    trials: list[tuple[CompositeRule, CompositeRule]] = []
    for extra in entry_cands:
        trials.append((_with_conjunct(entry, extra), exit_rule))
    for extra in exit_cands:
        trials.append((entry, _with_conjunct(exit_rule, extra)))
    for e_extra in entry_cands[:3]:
        for x_extra in exit_cands[:3]:
            trials.append((_with_conjunct(entry, e_extra), _with_conjunct(exit_rule, x_extra)))

    for er, xr in trials:
        if time.perf_counter() - t0 > time_budget_s:
            break
        net = _fee_net(df, cols, er, xr, fee=fee, stake_usd=stake_usd, n=n)
        if net is None:
            continue
        if net <= baseline_net + 1e-9:
            continue
        if best is None or net > best[2]:
            best = (er, xr, net)

    if best is None:
        return None
    return best[0], best[1], best[2], _FAMILY


def _extra_conjuncts(
    feats: list[dict[str, float]],
    labeled: list[int],
    keys: tuple[str, ...],
    *,
    strategy_id: str,
    side: str,
    existing: tuple[RuleConjunct, ...],
) -> list[RuleConjunct]:
    if len(labeled) < 1:
        return []
    # pick_rules needs ≥2 labels; duplicate single residual for fit robustness.
    labels = labeled if len(labeled) >= 2 else [labeled[0], labeled[0]]
    rules = pick_rules_at_labels(feats, labels, keys, strategy_id=strategy_id, side=side, k=6)
    existing_feats = {c.feature for c in existing}
    out: list[RuleConjunct] = []
    seen: set[tuple[str, str, float]] = set()
    for rule in rules:
        for c in rule.conjuncts:
            if c.feature in existing_feats:
                continue
            sig = (c.feature, c.op, float(c.value))
            if sig in seen:
                continue
            seen.add(sig)
            out.append(c)
            if len(out) >= 8:
                return out
    return out


def _with_conjunct(rule: CompositeRule, extra: RuleConjunct) -> CompositeRule:
    return CompositeRule(
        strategy_id=rule.strategy_id,
        conjuncts=tuple(list(rule.conjuncts) + [extra])[:3],
        rationale=f"{rule.rationale}; residual AND",
        requires_backtest=getattr(rule, "requires_backtest", True),
    )


def _fee_net(
    df: pd.DataFrame,
    cols: dict[str, Any],
    entry: CompositeRule,
    exit_rule: CompositeRule,
    *,
    fee: ExchangeFeeSchedule,
    stake_usd: float,
    n: int,
) -> float | None:
    em = mask_conjuncts(cols, entry.conjuncts)
    xm = mask_conjuncts(cols, exit_rule.conjuncts)
    if not em.any() or not xm.any():
        return None
    if (em.sum() / n) > _MAX_ENTRY_FRAC or (xm.sum() / n) > _MAX_EXIT_FRAC:
        return None
    best = float("-inf")
    for tsl in (0.0, 0.02, 0.03, 0.05):
        stats = simulate_long_with_fees(
            df, em, xm, stake_usd=stake_usd, fee=fee, trailing_stop_pct=tsl
        )
        trades = int(stats.get("trades") or 0)
        if trades < 1 or trades > _MAX_TRADES:
            continue
        trial = float(stats.get("net_profit") or 0.0)
        if trial > best:
            best = trial
    return None if best == float("-inf") else best


def _expand(indexes: list[int], n: int) -> list[int]:
    out: set[int] = set()
    for i in indexes:
        for d in (-1, 0, 1):
            j = i + d
            if 0 <= j < n:
                out.add(j)
    return sorted(out)
