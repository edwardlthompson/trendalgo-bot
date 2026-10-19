"""P&L-guided causal rule search for Secret Sauce (no future peek)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from trendalgo.backtest.oracle_pattern_mine import CompositeRule, RuleConjunct
from trendalgo.backtest.secret_sauce_features import match_feat
from trendalgo.backtest.secret_sauce_seeds import classic_pair_seeds
from trendalgo.backtest.ta_simulator import simulate_long_with_fees
from trendalgo.exchanges.fees import ExchangeFeeSchedule

_MAX_CANDS = 96
_TOP_PAIR = 18
_QUANTILES = (20, 35, 50, 65, 80)
_MAX_ENTRY_FIRE = 0.12  # fraction of bars
_MAX_EXIT_FIRE = 0.25
_MAX_TRADES_MULT = 1.5  # vs oracle swing count


def candidate_conjuncts(
    feats: list[dict[str, float]],
    labeled: list[int],
    keys: tuple[str, ...],
) -> list[RuleConjunct]:
    if not labeled:
        return []
    out: list[RuleConjunct] = [
        RuleConjunct(feature="local_trough", op=">=", value=1.0),
        RuleConjunct(feature="local_peak", op=">=", value=1.0),
        RuleConjunct(feature="trough_confirm", op=">=", value=1.0),
        RuleConjunct(feature="peak_confirm", op=">=", value=1.0),
    ]
    # Classic TA levels (honest, causal) — often beat label-median thresholds.
    for thr in (25.0, 30.0, 35.0, 40.0, 45.0):
        out.append(RuleConjunct(feature="rsi_14", op="<=", value=thr))
        out.append(RuleConjunct(feature="stoch_k", op="<=", value=thr))
    for thr in (55.0, 60.0, 65.0, 70.0, 75.0, 80.0, 85.0, 90.0):
        out.append(RuleConjunct(feature="rsi_14", op=">=", value=thr))
        out.append(RuleConjunct(feature="stoch_k", op=">=", value=thr))
    for thr in (0.15, 0.2, 0.25, 0.3):
        out.append(RuleConjunct(feature="bb_pct_b", op="<=", value=thr))
    for thr in (0.7, 0.75, 0.8, 0.85):
        out.append(RuleConjunct(feature="bb_pct_b", op=">=", value=thr))
    for thr in (1.0, 1.2, 1.5, 2.0):
        out.append(RuleConjunct(feature="vol_ratio", op=">=", value=thr))
    out.append(RuleConjunct(feature="above_sma20", op=">=", value=1.0))
    out.append(RuleConjunct(feature="above_sma50", op=">=", value=1.0))
    for key in keys:
        lab = np.array([float(feats[i].get(key) or 0.0) for i in labeled], dtype=float)
        allv = np.array([float(f.get(key) or 0.0) for f in feats], dtype=float)
        if lab.size == 0:
            continue
        s_med = float(np.median(lab))
        g_med = float(np.median(allv))
        prefer_high = s_med >= g_med
        for q in _QUANTILES:
            thr = float(np.percentile(lab, q))
            out.append(
                RuleConjunct(
                    feature=key,
                    op=">=" if prefer_high else "<=",
                    value=round(thr, 6),
                )
            )
        # Push toward labeled extreme for sparsity.
        if prefer_high:
            out.append(
                RuleConjunct(feature=key, op=">=", value=round(float(np.percentile(lab, 60)), 6))
            )
            out.append(
                RuleConjunct(feature=key, op=">=", value=round(float(np.percentile(lab, 75)), 6))
            )
        else:
            out.append(
                RuleConjunct(feature=key, op="<=", value=round(float(np.percentile(lab, 40)), 6))
            )
            out.append(
                RuleConjunct(feature=key, op="<=", value=round(float(np.percentile(lab, 25)), 6))
            )
        _ = g_med  # kept for clarity vs prior miner
    seen: set[tuple[str, str, float]] = set()
    uniq: list[RuleConjunct] = []
    for c in out:
        sig = (c.feature, c.op, c.value)
        if sig in seen:
            continue
        seen.add(sig)
        uniq.append(c)
    return uniq[:_MAX_CANDS]


def mask_for(feats: list[dict[str, float]], conjuncts: tuple[RuleConjunct, ...]) -> np.ndarray:
    m = np.zeros(len(feats), dtype=bool)
    for i, feat in enumerate(feats):
        if match_feat(feat, conjuncts):
            m[i] = True
    return m


def score_rule(
    feats: list[dict[str, float]],
    conjuncts: tuple[RuleConjunct, ...],
    labeled: list[int],
) -> float:
    if not conjuncts or not labeled:
        return -1.0
    m = mask_for(feats, conjuncts)
    # Exact + near (±2) hits — rewards rules that track oracle bars without flooding.
    exact = sum(1 for i in labeled if m[i])
    near = sum(1 for i in labeled if m[max(0, i - 2) : i + 3].any())
    if near == 0:
        return -1.0
    fire = int(m.sum())
    frac = fire / max(1, len(feats))
    if frac > 0.40:
        return -1.0
    cov = near / len(labeled)
    prec = near / max(1, fire)
    return cov * prec * (1.0 - frac) + 0.15 * (exact / len(labeled))


def _band_rules(
    feats: list[dict[str, float]],
    labeled: list[int],
    keys: tuple[str, ...],
    *,
    strategy_id: str,
    side: str,
) -> list[CompositeRule]:
    """IQR / central-band rules around labeled bars (tighter than one-sided cuts)."""
    rules: list[CompositeRule] = []
    for key in keys:
        lab = np.array([float(feats[i].get(key) or 0.0) for i in labeled], dtype=float)
        if lab.size < 2:
            continue
        for lo_q, hi_q in ((25, 75), (20, 80), (30, 70), (10, 90)):
            lo = float(np.percentile(lab, lo_q))
            hi = float(np.percentile(lab, hi_q))
            if hi < lo:
                lo, hi = hi, lo
            conj = (
                RuleConjunct(feature=key, op=">=", value=round(lo, 6)),
                RuleConjunct(feature=key, op="<=", value=round(hi, 6)),
            )
            sc = score_rule(feats, conj, labeled)
            if sc <= 0:
                continue
            rules.append(
                CompositeRule(
                    strategy_id=strategy_id,
                    conjuncts=conj,
                    rationale=f"Secret Sauce {side} band {key}.",
                )
            )
    return rules


def pick_top_rules(
    feats: list[dict[str, float]],
    labeled: list[int],
    keys: tuple[str, ...],
    *,
    strategy_id: str,
    side: str,
    k: int = _TOP_PAIR,
) -> list[CompositeRule]:
    cands = candidate_conjuncts(feats, labeled, keys)
    scored: list[tuple[float, CompositeRule]] = []
    for c in cands:
        conj = (c,)
        sc = score_rule(feats, conj, labeled)
        if sc <= 0:
            continue
        scored.append(
            (
                sc,
                CompositeRule(
                    strategy_id=strategy_id,
                    conjuncts=conj,
                    rationale=f"Secret Sauce {side} (P&L search).",
                ),
            )
        )
    for rule in _band_rules(feats, labeled, keys, strategy_id=strategy_id, side=side):
        scored.append((score_rule(feats, rule.conjuncts, labeled), rule))
    scored.sort(key=lambda t: t[0], reverse=True)
    top = [r for _, r in scored[:20]]
    for i, a in enumerate(top):
        for b in top[i + 1 :]:
            fa = {c.feature for c in a.conjuncts}
            fb = {c.feature for c in b.conjuncts}
            if fa & fb:
                continue
            merged = list(a.conjuncts) + list(b.conjuncts)
            and_conj: tuple[RuleConjunct, ...] = tuple(merged[:3])
            sc = score_rule(feats, and_conj, labeled)
            if sc <= 0:
                continue
            scored.append(
                (
                    sc,
                    CompositeRule(
                        strategy_id=strategy_id,
                        conjuncts=and_conj,
                        rationale=f"Secret Sauce {side} (P&L search AND).",
                    ),
                )
            )
    scored.sort(key=lambda t: t[0], reverse=True)
    seen: set[str] = set()
    rules: list[CompositeRule] = []
    for _, rule in scored:
        sig = "|".join(f"{c.feature}{c.op}{c.value}" for c in rule.conjuncts)
        if sig in seen:
            continue
        seen.add(sig)
        rules.append(rule)
        if len(rules) >= k:
            break
    # Always seed classic single-conjunct TA levels into the P&L cross (bypass label score).
    seeds = candidate_conjuncts(feats, labeled, keys) if labeled else []
    for c in seeds:
        if c.feature not in {
            "rsi_14",
            "stoch_k",
            "bb_pct_b",
            "vol_ratio",
            "trough_confirm",
            "peak_confirm",
            "above_sma20",
            "above_sma50",
        }:
            continue
        if (
            side == "entry" and c.op == ">=" and c.feature in {"rsi_14", "stoch_k", "bb_pct_b"}
        ) or (side == "exit" and c.op == "<=" and c.feature in {"rsi_14", "stoch_k", "bb_pct_b"}):
            continue
        rule = CompositeRule(
            strategy_id=strategy_id,
            conjuncts=(c,),
            rationale=f"Secret Sauce {side} classic seed.",
        )
        sig = "|".join(f"{x.feature}{x.op}{x.value}" for x in rule.conjuncts)
        if sig in seen:
            continue
        seen.add(sig)
        rules.append(rule)
    return rules[: max(k, 24)]


def best_entry_exit_by_pnl(
    df: pd.DataFrame,
    feats: list[dict[str, float]],
    *,
    entry_rules: list[CompositeRule],
    exit_rules: list[CompositeRule],
    fee: ExchangeFeeSchedule,
    stake_usd: float,
    n_swings: int,
    bh_net: float | None = None,
) -> tuple[CompositeRule, CompositeRule, float] | None:
    """Cross top entry×exit; max Net % after fees with progressive sparsity caps."""
    n = len(feats)
    # Ensure classic pairs participate in the search.
    sid = entry_rules[0].strategy_id if entry_rules else "GEN_SECRET_1"
    for er, xr in classic_pair_seeds(sid):
        entry_rules = [*entry_rules, er]
        exit_rules = [*exit_rules, xr]
    entry_masks = [mask_for(feats, r.conjuncts) for r in entry_rules]
    exit_masks = [mask_for(feats, r.conjuncts) for r in exit_rules]
    schedules = (
        (_MAX_ENTRY_FIRE, _MAX_EXIT_FIRE, _MAX_TRADES_MULT),
        (0.20, 0.40, 2.5),
        (0.35, 0.55, 4.0),
        (0.55, 0.80, 8.0),
    )
    overall: tuple[CompositeRule, CompositeRule, float] | None = None
    best_pos: tuple[CompositeRule, CompositeRule, float] | None = None
    best_vs_bh: tuple[CompositeRule, CompositeRule, float] | None = None
    for max_ef, max_xf, tmult in schedules:
        max_trades = max(2, int(n_swings * tmult))
        for er, em in zip(entry_rules, entry_masks, strict=True):
            if not em.any() or (em.sum() / n) > max_ef:
                continue
            for xr, xm in zip(exit_rules, exit_masks, strict=True):
                if not xm.any() or (xm.sum() / n) > max_xf:
                    continue
                stats = simulate_long_with_fees(
                    df, em, xm, stake_usd=stake_usd, fee=fee, trailing_stop_pct=0.0
                )
                trades = int(stats.get("trades") or 0)
                if trades < 1 or trades > max_trades:
                    continue
                net = float(stats.get("net_profit") or 0.0)
                cand = (er, xr, net)
                if overall is None or net > overall[2]:
                    overall = cand
                if net > 0 and (best_pos is None or net > best_pos[2]):
                    best_pos = cand
                if (
                    bh_net is not None
                    and net > bh_net
                    and (best_vs_bh is None or net > best_vs_bh[2])
                ):
                    best_vs_bh = cand
    if best_vs_bh is not None:
        return best_vs_bh
    if best_pos is not None:
        return best_pos
    return overall


def default_search_fee() -> ExchangeFeeSchedule:
    """Retail-like fee so search does not reward churn."""
    return ExchangeFeeSchedule(
        exchange_id="ss-search",
        taker_pct=0.002,
        maker_pct=0.001,
        tier="retail",
        source_url="",
    )


def causal_swing_masks(df: pd.DataFrame, *, window: int = 5) -> tuple[np.ndarray, np.ndarray]:
    """Causal local-trough entries / local-peak exits (bars ≤ i only)."""
    lows = (
        df["low"].to_numpy(dtype=float)
        if "low" in df.columns
        else df["close"].to_numpy(dtype=float)
    )
    highs = (
        df["high"].to_numpy(dtype=float)
        if "high" in df.columns
        else df["close"].to_numpy(dtype=float)
    )
    n = len(df)
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)
    w = max(2, int(window))
    for i in range(n):
        lo_past = lows[max(0, i - w) : i + 1]
        hi_past = highs[max(0, i - w) : i + 1]
        if lows[i] <= float(np.min(lo_past)):
            entries[i] = True
        if highs[i] >= float(np.max(hi_past)):
            exits[i] = True
    return entries, exits


def swing_rules(strategy_id: str, window: int) -> tuple[CompositeRule, CompositeRule]:
    """Synthetic rules representing causal swing detector (for dossier English)."""
    entry = CompositeRule(
        strategy_id=strategy_id,
        conjuncts=(RuleConjunct(feature="dist_low_5", op="<=", value=0.0),),
        rationale=f"causal local trough w={window}",
    )
    exit_r = CompositeRule(
        strategy_id=strategy_id,
        conjuncts=(RuleConjunct(feature="dist_high_5", op="<=", value=0.0),),
        rationale=f"causal local peak w={window}",
    )
    return entry, exit_r
