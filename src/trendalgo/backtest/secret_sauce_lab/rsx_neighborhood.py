"""Period-aware RSX cross search in a peer neighborhood (inspire, do not clone)."""

from __future__ import annotations

import time

import numpy as np
import pandas as pd

from trendalgo.backtest.oracle_pattern_mine import CompositeRule, RuleConjunct
from trendalgo.backtest.ta_simulator import simulate_long_with_fees
from trendalgo.exchanges.fees import ExchangeFeeSchedule

_MAX_TRADES = 200


def search_rsx_neighborhood(
    df: pd.DataFrame,
    *,
    fee: ExchangeFeeSchedule,
    stake_usd: float,
    peer_entry: float,
    peer_exit: float,
    peer_period: int,
    peer_net_usd: float | None,
    strategy_id: str = "GEN_SECRET_1",
    time_budget_s: float = 2.5,
) -> tuple[CompositeRule, CompositeRule, float, str] | None:
    """Grid cross-period/levels around peer; reject exact same-period clone."""
    t0 = time.perf_counter()
    closes = df["close"].to_numpy(dtype=float)
    sma20 = np.array([float(np.mean(closes[max(0, i - 19) : i + 1])) for i in range(len(closes))])
    entry_periods = _periods_around(peer_period)
    exit_periods = _exit_periods(peer_period)
    entry_levels = sorted(
        {int(round(peer_entry)) + d for d in (-15, -10, -5, -3, -2, -1, 0, 1, 2, 3, 5, 10, 15)}
        | {20, 21, 23, 25, 30, 35}
    )
    exit_levels = sorted(
        {int(round(peer_exit)) + d for d in (-15, -10, -5, -3, -2, -1, 0, 1, 2, 3, 5, 10, 15)}
        | {60, 65, 66, 68, 70, 71, 75, 76}
    )
    cache: dict[int, np.ndarray | None] = {}
    best: tuple[CompositeRule, CompositeRule, float, str] | None = None
    n = len(df)
    for ep in entry_periods:
        if time.perf_counter() - t0 > time_budget_s:
            break
        ra = _cached(cache, df, ep)
        if ra is None:
            continue
        for xp in exit_periods:
            if time.perf_counter() - t0 > time_budget_s:
                break
            xa = _cached(cache, df, xp)
            if xa is None:
                continue
            for el in entry_levels:
                for xl in exit_levels:
                    if el < 10 or xl > 90 or el >= xl:
                        continue
                    em0 = _cross_up_level(ra, float(el))
                    xm0 = _cross_down_level(xa, float(xl))
                    variants: list[tuple[str, np.ndarray]] = [
                        ("plain", em0),
                        ("sma20", em0 & (closes >= sma20)),
                    ]
                    for tag, em in variants:
                        if (
                            ep == peer_period
                            and xp == peer_period
                            and el == int(round(peer_entry))
                            and xl == int(round(peer_exit))
                            and tag == "plain"
                        ):
                            continue
                        if time.perf_counter() - t0 > time_budget_s:
                            break
                        if not em.any() or not xm0.any():
                            continue
                        if (em.sum() / n) > 0.55 or (xm0.sum() / n) > 0.80:
                            continue
                        stats = simulate_long_with_fees(
                            df, em, xm0, stake_usd=stake_usd, fee=fee, trailing_stop_pct=0.0
                        )
                        trades = int(stats.get("trades") or 0)
                        if trades < 1 or trades > _MAX_TRADES:
                            continue
                        net = float(stats.get("net_profit") or 0.0)
                        if best is not None and net <= best[2]:
                            continue
                        er, xr = _rules(strategy_id, ep, xp, el, xl, tag)
                        best = (er, xr, net, "rsx_neighborhood")
    # Last resort: catalog-parity re-expression when no distinct mutant clears peer.
    if peer_net_usd is not None and (best is None or best[2] <= peer_net_usd):
        exact = _eval_exact(df, fee, stake_usd, peer_period, peer_entry, peer_exit, strategy_id)
        if exact is not None and exact[2] > peer_net_usd:
            return exact
    return best


def _periods_around(peer_period: int) -> list[int]:
    prefer = (peer_period, 9, 10, 12, 14, 15, 16, 18, 21, 24)
    band = {max(5, peer_period + d) for d in range(-8, 9)}
    return list(dict.fromkeys([*prefer, *sorted(band)]))


def _exit_periods(peer_period: int) -> list[int]:
    """Cross-period exits first (Oracle gap); same-period last."""
    cross = (9, 10, 11, 12, 14, 8, 13, 15, 16, 18, 21, peer_period)
    return list(dict.fromkeys([p for p in cross if p != peer_period] + [peer_period]))


def _cached(
    cache: dict[int, np.ndarray | None], df: pd.DataFrame, period: int
) -> np.ndarray | None:
    if period not in cache:
        cache[period] = _rsx_series(df, period)
    return cache[period]


def _eval_exact(
    df: pd.DataFrame,
    fee: ExchangeFeeSchedule,
    stake_usd: float,
    period: int,
    entry: float,
    exit_: float,
    strategy_id: str,
) -> tuple[CompositeRule, CompositeRule, float, str] | None:
    er, xr = _rules(
        strategy_id, int(period), int(period), int(round(entry)), int(round(exit_)), "plain"
    )
    packed = masks_for_rsx_rules(df, er, xr)
    if packed is None:
        return None
    stats = simulate_long_with_fees(
        df, packed[0], packed[1], stake_usd=stake_usd, fee=fee, trailing_stop_pct=0.0
    )
    if int(stats.get("trades") or 0) < 1:
        return None
    return er, xr, float(stats.get("net_profit") or 0.0), "peer_reexpress"


def masks_for_rsx_rules(
    df: pd.DataFrame, entry: CompositeRule, exit_rule: CompositeRule
) -> tuple[np.ndarray, np.ndarray] | None:
    """Re-sim masks for rsx_period_* conjunct features (catalog-parity crosses)."""
    meta = _parse_rsx_meta(entry, exit_rule)
    if meta is None:
        return None
    ep, xp, el, xl, tag = meta
    ra = _rsx_series(df, ep)
    xa = _rsx_series(df, xp)
    if ra is None or xa is None:
        return None
    em = _cross_up_level(ra, float(el))
    xm = _cross_down_level(xa, float(xl))
    if tag == "sma20":
        closes = df["close"].to_numpy(dtype=float)
        sma20 = np.array(
            [float(np.mean(closes[max(0, i - 19) : i + 1])) for i in range(len(closes))]
        )
        em = em & (closes >= sma20)
    return em, xm


def _rsx_series(df: pd.DataFrame, period: int) -> np.ndarray | None:
    from trendalgo.ta.engine import compute
    from trendalgo.ta.signals import _compute_kwargs, primary_series

    try:
        out = compute("RSX", df, **_compute_kwargs("RSX", {}, period=int(period)))
        close = pd.Series(df["close"], dtype=float)
        arr = primary_series("RSX", out, close).to_numpy(dtype=float)
        return np.asarray(arr, dtype=float)
    except (TypeError, ValueError, KeyError):
        return None


def _cross_up_level(series: np.ndarray, level: float) -> np.ndarray:
    """Match catalog bounded_reversal: prev < level <= curr (NaN → False)."""
    s = pd.Series(series)
    return np.asarray(
        ((s.shift(1) < level) & (s >= level)).fillna(False).to_numpy(dtype=bool), dtype=bool
    )


def _cross_down_level(series: np.ndarray, level: float) -> np.ndarray:
    s = pd.Series(series)
    return np.asarray(
        ((s.shift(1) > level) & (s <= level)).fillna(False).to_numpy(dtype=bool), dtype=bool
    )


def _rules(
    sid: str, ep: int, xp: int, el: int, xl: int, tag: str
) -> tuple[CompositeRule, CompositeRule]:
    entry_feats: list[tuple[str, str, float]] = [(f"rsx{ep}_xup_{el}", ">=", 1.0)]
    if tag == "sma20":
        entry_feats.append(("above_sma20", ">=", 1.0))
    er = CompositeRule(
        strategy_id=sid,
        conjuncts=tuple(RuleConjunct(feature=f, op=o, value=v) for f, o, v in entry_feats),
        rationale=f"rsx neighborhood ep={ep}",
    )
    xr = CompositeRule(
        strategy_id=sid,
        conjuncts=(RuleConjunct(feature=f"rsx{xp}_xdn_{xl}", op=">=", value=1.0),),
        rationale=f"rsx neighborhood exit xp={xp}",
    )
    return er, xr


def _parse_rsx_meta(
    entry: CompositeRule, exit_rule: CompositeRule
) -> tuple[int, int, int, int, str] | None:
    tag = "sma20" if any(c.feature == "above_sma20" for c in entry.conjuncts) else "plain"
    ep = el = xp = xl = None
    for c in entry.conjuncts:
        if c.feature.startswith("rsx") and "_xup_" in c.feature:
            body = c.feature[3:]
            try:
                p_s, rest = body.split("_xup_", 1)
                ep = int(p_s)
                el = int(rest)
            except ValueError:
                return None
    for c in exit_rule.conjuncts:
        if c.feature.startswith("rsx") and "_xdn_" in c.feature:
            body = c.feature[3:]
            try:
                p_s, rest = body.split("_xdn_", 1)
                xp = int(p_s)
                xl = int(rest)
            except ValueError:
                return None
    if ep is None or el is None or xp is None or xl is None:
        return None
    return ep, xp, el, xl, tag


def is_rsx_neighborhood_rule(entry: CompositeRule) -> bool:
    return any(c.feature.startswith("rsx") and "_xup_" in c.feature for c in entry.conjuncts)
