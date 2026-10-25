"""AND pivot/VWAP/POC gates onto Sauce TA catalog masks when fee Net improves."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from trendalgo.backtest.secret_sauce_features import causal_features, match_feat
from trendalgo.backtest.secret_sauce_lab.label_rules import pick_rules_at_labels
from trendalgo.backtest.secret_sauce_pivots import PIVOT_KEYS
from trendalgo.backtest.secret_sauce_structure import STRUCTURE_KEYS
from trendalgo.backtest.ta_simulator import simulate_long_with_fees

_GATE_KEYS = PIVOT_KEYS + STRUCTURE_KEYS
_MAX_ENTRY_FRAC = 0.55
_MAX_TRADES = 200


def refine_masks_with_pivots(
    df: pd.DataFrame,
    entries: np.ndarray,
    exits: np.ndarray,
    *,
    entry_labels: list[int],
    exit_labels: list[int],
    fee: Any,
    stake: float,
    trailing_stop_pct: float,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any], str | None]:
    """Try AND-ing one pivot conjunct on entry and/or exit; keep fee-Net lifts only."""
    base = simulate_long_with_fees(
        df,
        entries,
        exits,
        stake_usd=stake,
        fee=fee,
        trailing_stop_pct=trailing_stop_pct,
        collect_trades=True,
    )
    baseline = float(base.get("net_profit") or 0.0)
    feats = causal_features(df)
    if not feats:
        return entries, exits, base, None
    residual_e = [i for i in entry_labels if 0 <= i < len(entries) and not bool(entries[i])]
    residual_x = [i for i in exit_labels if 0 <= i < len(exits) and not bool(exits[i])]
    # Prefer residual Oracle bars; fall back to all labels so gates still learn.
    e_fit = residual_e if len(residual_e) >= 1 else list(entry_labels)
    x_fit = residual_x if len(residual_x) >= 1 else list(exit_labels)
    e_cons = _pivot_conjuncts(feats, e_fit, side="entry")
    x_cons = _pivot_conjuncts(feats, x_fit, side="exit")
    best_e, best_x, best_stats, tag = entries, exits, base, None
    best_net = baseline
    trials: list[tuple[np.ndarray, np.ndarray, str]] = []
    for conj in e_cons[:4]:
        gate = np.array([match_feat(f, (conj,)) for f in feats], dtype=bool)
        trials.append((entries & gate, exits, f"entry:{conj.feature}"))
    for conj in x_cons[:4]:
        gate = np.array([match_feat(f, (conj,)) for f in feats], dtype=bool)
        trials.append((entries, exits & gate, f"exit:{conj.feature}"))
    for e_c in e_cons[:2]:
        for x_c in x_cons[:2]:
            eg = np.array([match_feat(f, (e_c,)) for f in feats], dtype=bool)
            xg = np.array([match_feat(f, (x_c,)) for f in feats], dtype=bool)
            trials.append((entries & eg, exits & xg, f"both:{e_c.feature}+{x_c.feature}"))
    n = len(df)
    for em, xm, name in trials:
        if not em.any() or not xm.any():
            continue
        if (em.sum() / n) > _MAX_ENTRY_FRAC:
            continue
        stats = simulate_long_with_fees(
            df,
            em,
            xm,
            stake_usd=stake,
            fee=fee,
            trailing_stop_pct=trailing_stop_pct,
            collect_trades=True,
        )
        trades = int(stats.get("trades") or 0)
        if trades < 1 or trades > _MAX_TRADES:
            continue
        net = float(stats.get("net_profit") or 0.0)
        if net > best_net + 1e-9:
            best_e, best_x, best_stats, tag, best_net = em, xm, stats, name, net
    return best_e, best_x, best_stats, tag


def _pivot_conjuncts(feats: list[dict[str, float]], labels: list[int], *, side: str) -> list[Any]:
    from trendalgo.backtest.oracle_pattern_mine import RuleConjunct

    if len(labels) < 1:
        return []
    fit = labels if len(labels) >= 2 else [labels[0], labels[0]]
    rules = pick_rules_at_labels(feats, fit, _GATE_KEYS, strategy_id="GEN_SECRET_1", side=side, k=6)
    out: list[RuleConjunct] = []
    seen: set[tuple[str, str, float]] = set()
    for rule in rules:
        for c in rule.conjuncts:
            if c.feature not in _GATE_KEYS:
                continue
            sig = (c.feature, c.op, float(c.value))
            if sig in seen:
                continue
            seen.add(sig)
            out.append(c)
    return out
