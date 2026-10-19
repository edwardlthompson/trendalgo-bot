"""Discriminative conjunct fit at labeled bars (causal features only)."""

from __future__ import annotations

import numpy as np

from trendalgo.backtest.oracle_pattern_mine import CompositeRule, RuleConjunct
from trendalgo.backtest.secret_sauce_features import match_feat

_QUANTILES = (25, 50, 75)
_MAX_FIRE = 0.40
_TOP_K = 12
_MAX_CANDS = 48


def score_labeled(
    feats: list[dict[str, float]],
    conjuncts: tuple[RuleConjunct, ...],
    labeled: list[int],
) -> float:
    """Coverage × precision with fire-rate cap (near ±2 bars)."""
    if not conjuncts or not labeled:
        return -1.0
    m = _mask(feats, conjuncts)
    exact = sum(1 for i in labeled if m[i])
    near = sum(1 for i in labeled if m[max(0, i - 2) : i + 3].any())
    if near == 0:
        return -1.0
    fire = int(m.sum())
    frac = fire / max(1, len(feats))
    if frac > _MAX_FIRE:
        return -1.0
    cov = near / len(labeled)
    prec = near / max(1, fire)
    return cov * prec * (1.0 - frac) + 0.15 * (exact / len(labeled))


def pick_rules_at_labels(
    feats: list[dict[str, float]],
    labeled: list[int],
    keys: tuple[str, ...],
    *,
    strategy_id: str,
    side: str,
    k: int = _TOP_K,
) -> list[CompositeRule]:
    """Top-k single/AND rules fitted to labeled bars."""
    if len(labeled) < 2 or not feats:
        return []
    scored: list[tuple[float, CompositeRule]] = []
    for c in _candidates(feats, labeled, keys):
        sc = score_labeled(feats, (c,), labeled)
        if sc <= 0:
            continue
        scored.append(
            (
                sc,
                CompositeRule(
                    strategy_id=strategy_id,
                    conjuncts=(c,),
                    rationale=f"pattern {side}",
                ),
            )
        )
    scored.sort(key=lambda t: t[0], reverse=True)
    top = [r for _, r in scored[:12]]
    for i, a in enumerate(top):
        for b in top[i + 1 :]:
            fa = {c.feature for c in a.conjuncts}
            fb = {c.feature for c in b.conjuncts}
            if fa & fb:
                continue
            merged = tuple(list(a.conjuncts) + list(b.conjuncts))[:2]
            sc = score_labeled(feats, merged, labeled)
            if sc <= 0:
                continue
            scored.append(
                (
                    sc,
                    CompositeRule(
                        strategy_id=strategy_id,
                        conjuncts=merged,
                        rationale=f"pattern {side} and",
                    ),
                )
            )
    scored.sort(key=lambda t: t[0], reverse=True)
    seen: set[str] = set()
    out: list[CompositeRule] = []
    for _, rule in scored:
        sig = "|".join(f"{c.feature}{c.op}{c.value}" for c in rule.conjuncts)
        if sig in seen:
            continue
        seen.add(sig)
        out.append(rule)
        if len(out) >= k:
            break
    return out


def _candidates(
    feats: list[dict[str, float]],
    labeled: list[int],
    keys: tuple[str, ...],
) -> list[RuleConjunct]:
    out: list[RuleConjunct] = [
        RuleConjunct(feature="trough_confirm", op=">=", value=1.0),
        RuleConjunct(feature="peak_confirm", op=">=", value=1.0),
        RuleConjunct(feature="local_trough", op=">=", value=1.0),
        RuleConjunct(feature="local_peak", op=">=", value=1.0),
        RuleConjunct(feature="above_sma20", op=">=", value=1.0),
        RuleConjunct(feature="above_sma50", op=">=", value=1.0),
    ]
    seps: list[tuple[float, str]] = []
    for key in keys:
        lab = np.array([float(feats[i].get(key) or 0.0) for i in labeled], dtype=float)
        allv = np.array([float(f.get(key) or 0.0) for f in feats], dtype=float)
        if lab.size == 0:
            continue
        seps.append((abs(float(np.median(lab)) - float(np.median(allv))), key))
    seps.sort(reverse=True)
    for _sep, key in seps[:16]:
        lab = np.array([float(feats[i].get(key) or 0.0) for i in labeled], dtype=float)
        allv = np.array([float(f.get(key) or 0.0) for f in feats], dtype=float)
        prefer_high = float(np.median(lab)) >= float(np.median(allv))
        for q in _QUANTILES:
            out.append(
                RuleConjunct(
                    feature=key,
                    op=">=" if prefer_high else "<=",
                    value=round(float(np.percentile(lab, q)), 6),
                )
            )
    seen: set[tuple[str, str, float]] = set()
    uniq: list[RuleConjunct] = []
    for c in out:
        sig = (c.feature, c.op, c.value)
        if sig in seen:
            continue
        seen.add(sig)
        uniq.append(c)
    return uniq[:_MAX_CANDS]


def _mask(feats: list[dict[str, float]], conjuncts: tuple[RuleConjunct, ...]) -> np.ndarray:
    m = np.zeros(len(feats), dtype=bool)
    for i, feat in enumerate(feats):
        if match_feat(feat, conjuncts):
            m[i] = True
    return m
