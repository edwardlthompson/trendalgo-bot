"""Reverse-mine Enter/Exit seed pairs from labeled trade bars."""

from __future__ import annotations

import time
from typing import Any

import pandas as pd

from trendalgo.backtest.oracle_pattern_mine import CompositeRule
from trendalgo.backtest.secret_sauce_features import feature_keys_for
from trendalgo.backtest.secret_sauce_lab.columnar import feature_matrix, mask_conjuncts
from trendalgo.backtest.secret_sauce_lab.label_rules import pick_rules_at_labels, score_labeled
from trendalgo.backtest.ta_simulator import simulate_long_with_fees

_MAX_PAIRS = 16
_TIME_BUDGET_S = 0.6
_MAX_ENTRY_FRAC = 0.55
_MAX_EXIT_FRAC = 0.80
_MAX_TRADES = 200


def pattern_seed_pairs(
    df: pd.DataFrame,
    *,
    entry_indexes: list[int],
    exit_indexes: list[int],
    strategy_id: str = "GEN_SECRET_1",
    family: str = "oracle_pattern",
    time_budget_s: float = _TIME_BUDGET_S,
    fee: Any | None = None,
    stake_usd: float | None = None,
) -> list[tuple[CompositeRule, CompositeRule, str]]:
    """Fit causal entry/exit rules at labeled bars; fee-rank when fee+stake given."""
    # Expand ±1 bar so fit is robust to single-bar pivot jitter.
    entries = _expand(entry_indexes, len(df))
    exits = _expand(exit_indexes, len(df))
    if len(entries) < 2 or len(exits) < 1:
        return []
    t0 = time.perf_counter()
    cols, feats = feature_matrix(df)
    if not feats:
        return []
    keys = feature_keys_for(df)
    entry_rules = pick_rules_at_labels(
        feats, entries, keys, strategy_id=strategy_id, side="entry", k=8
    )
    if time.perf_counter() - t0 > time_budget_s:
        entry_rules = entry_rules[:4]
    exit_rules = pick_rules_at_labels(feats, exits, keys, strategy_id=strategy_id, side="exit", k=8)
    if not entry_rules or not exit_rules:
        return []
    # Cross top entries × exits; prefer fee Net % when available (Oracle direction).
    scored: list[tuple[float, CompositeRule, CompositeRule]] = []
    use_fee = fee is not None and stake_usd is not None and stake_usd > 0
    n = len(df)
    for er in entry_rules:
        for xr in exit_rules:
            if time.perf_counter() - t0 > time_budget_s:
                break
            if use_fee:
                assert fee is not None and stake_usd is not None
                em = mask_conjuncts(cols, er.conjuncts)
                xm = mask_conjuncts(cols, xr.conjuncts)
                if not em.any() or not xm.any():
                    continue
                if (em.sum() / n) > _MAX_ENTRY_FRAC or (xm.sum() / n) > _MAX_EXIT_FRAC:
                    continue
                stats = simulate_long_with_fees(
                    df, em, xm, stake_usd=float(stake_usd), fee=fee, trailing_stop_pct=0.0
                )
                trades = int(stats.get("trades") or 0)
                if trades < 1 or trades > _MAX_TRADES:
                    continue
                sc = float(stats.get("net_profit") or 0.0)
            else:
                sc_e = score_labeled(feats, er.conjuncts, entries)
                sc_x = score_labeled(feats, xr.conjuncts, exits)
                if sc_e <= 0 or sc_x <= 0:
                    continue
                sc = sc_e + sc_x
            scored.append((sc, er, xr))
        if time.perf_counter() - t0 > time_budget_s:
            break
    scored.sort(key=lambda t: t[0], reverse=True)
    out: list[tuple[CompositeRule, CompositeRule, str]] = []
    seen: set[str] = set()
    for _sc, er, xr in scored:
        sig = _sig(er, xr)
        if sig in seen:
            continue
        seen.add(sig)
        out.append((er, xr, family))
        if len(out) >= _MAX_PAIRS:
            break
    return out


def indexes_from_trades(trades: list[dict[str, Any]], *, n: int) -> tuple[list[int], list[int]]:
    """Pull entry/exit indexes from oracle_swings or peer trade dicts."""
    entries: list[int] = []
    exits: list[int] = []
    for t in trades:
        ei = _as_int(t.get("entry_index"), default=-1)
        xi = _as_int(t.get("exit_index"), default=-1)
        if 0 <= ei < n:
            entries.append(ei)
        if 0 <= xi < n:
            exits.append(xi)
    return entries, exits


def _as_int(raw: Any, *, default: int) -> int:
    if raw is None:
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def _expand(indexes: list[int], n: int) -> list[int]:
    out: list[int] = []
    seen: set[int] = set()
    for i in indexes:
        for j in (i - 1, i, i + 1):
            if 0 <= j < n and j not in seen:
                seen.add(j)
                out.append(j)
    return out


def _sig(er: CompositeRule, xr: CompositeRule) -> str:
    e = "|".join(f"{c.feature}{c.op}{c.value}" for c in er.conjuncts)
    x = "|".join(f"{c.feature}{c.op}{c.value}" for c in xr.conjuncts)
    return f"{e}=>{x}"
