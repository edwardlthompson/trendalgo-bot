"""Permutation null + threshold stability badges (SIM-08)."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from trendalgo.backtest.secret_sauce_lab.columnar import mask_conjuncts
from trendalgo.backtest.secret_sauce_lab.search import SearchHit
from trendalgo.backtest.ta_simulator import simulate_long_with_fees
from trendalgo.exchanges.fees import ExchangeFeeSchedule


def annotate_stability(
    hit: SearchHit,
    *,
    df: pd.DataFrame,
    cols: dict[str, np.ndarray],
    fee: ExchangeFeeSchedule,
    stake_usd: float,
    trial_count: int,
    null_draws: int = 12,
) -> SearchHit:
    """Attach null percentile + fragile/stable badge without changing selection."""
    del trial_count
    em = mask_conjuncts(cols, hit.entry.conjuncts)
    xm = mask_conjuncts(cols, hit.exit.conjuncts)
    base = float(hit.net)
    closes = df["close"].to_numpy(dtype=float)
    rets = np.diff(closes, prepend=closes[0])
    null_nets: list[float] = []
    rng = np.random.default_rng(0)
    for _ in range(max(4, null_draws)):
        shuffled = rng.permutation(rets)
        path = closes[0] + np.cumsum(shuffled)
        path[0] = closes[0]
        fake = df.copy()
        fake["close"] = path
        fake["open"] = path
        fake["high"] = path
        fake["low"] = path
        null_nets.append(
            float(
                simulate_long_with_fees(
                    fake,
                    em,
                    xm,
                    stake_usd=stake_usd,
                    fee=fee,
                    trailing_stop_pct=hit.trailing_stop_pct,
                ).get("net_profit")
                or 0.0
            )
        )
    pct = float(np.mean(np.asarray(null_nets, dtype=float) < base))
    badge = "stable"
    if pct < 0.95:
        badge = "not_distinguishable_from_chance"
    # Threshold ±1 quantile fragility: nudge conjunct values ±1% relative.
    fragile = _fragile_thresholds(hit, df=df, cols=cols, fee=fee, stake_usd=stake_usd, base=base)
    if fragile:
        badge = "fragile" if badge == "stable" else badge
    return hit._replace(null_percentile=round(pct, 4), stability=badge)


def _fragile_thresholds(
    hit: SearchHit,
    *,
    df: pd.DataFrame,
    cols: dict[str, np.ndarray],
    fee: ExchangeFeeSchedule,
    stake_usd: float,
    base: float,
) -> bool:
    from trendalgo.backtest.oracle_pattern_mine import CompositeRule, RuleConjunct

    if not hit.entry.conjuncts:
        return False
    conj = hit.entry.conjuncts[0]
    for scale in (0.99, 1.01):
        nudged = tuple(
            [
                RuleConjunct(feature=conj.feature, op=conj.op, value=float(conj.value) * scale),
                *hit.entry.conjuncts[1:],
            ]
        )
        er = CompositeRule(
            strategy_id=hit.entry.strategy_id,
            conjuncts=nudged,
            rationale=hit.entry.rationale,
        )
        em = mask_conjuncts(cols, er.conjuncts)
        xm = mask_conjuncts(cols, hit.exit.conjuncts)
        net = float(
            simulate_long_with_fees(
                df, em, xm, stake_usd=stake_usd, fee=fee, trailing_stop_pct=hit.trailing_stop_pct
            ).get("net_profit")
            or 0.0
        )
        if base > 0 and net < 0.5 * base:
            return True
    return False
