"""Time-boxed fee-aware P&L search — maximize Net % toward Oracle ceiling."""

from __future__ import annotations

import time
from typing import Any, NamedTuple

import numpy as np
import pandas as pd

from trendalgo.backtest.oracle_pattern_mine import CompositeRule
from trendalgo.backtest.secret_sauce_lab.columnar import feature_matrix, mask_conjuncts
from trendalgo.backtest.secret_sauce_lab.search_folds import (
    passes_holdout_gate,
    restrict_mask,
)
from trendalgo.backtest.secret_sauce_lab.search_metrics import enrich_trial_stats
from trendalgo.backtest.ta_simulator import simulate_long_with_fees
from trendalgo.exchanges.fees import ExchangeFeeSchedule

_TIME_BUDGET_S = 4.0
_MAX_ENTRY_FRAC = 0.55
_MAX_EXIT_FRAC = 0.80
_MAX_TRADES = 200
_MIN_TRADES = 1
_ORACLE_FAM = frozenset(
    {
        "oracle_pattern",
        "peer_pattern",
        "rsx_neighborhood",
        "osc_cross",
        "peer_reexpress",
        "residual_and",
        "adaptive_exit",
    }
)


class SearchHit(NamedTuple):
    entry: CompositeRule
    exit: CompositeRule
    net: float
    family: str
    trailing_stop_pct: float
    train_net: float | None = None
    holdout_net: float | None = None
    holdout_gate_ok: bool | None = None
    fee_drag_pct: float | None = None
    exposure_pct: float | None = None
    excess_vs_bh: float | None = None
    null_percentile: float | None = None
    stability: str | None = None


def search_best_pair(
    df: pd.DataFrame,
    pairs: list[tuple[CompositeRule, CompositeRule, str]],
    *,
    fee: ExchangeFeeSchedule,
    stake_usd: float,
    bh_net: float | None,
    time_budget_s: float = _TIME_BUDGET_S,
    peer_net: float | None = None,
    direction: str | None = None,
    train_indexes: list[int] | None = None,
    holdout_indexes: list[int] | None = None,
    purge_bars: int = 0,
) -> SearchHit | None:
    """Return best SearchHit (entry/exit/net/family/tsl + honesty metrics)."""
    del purge_bars  # applied by caller when building indexes
    cols, _feats = feature_matrix(df)
    n = len(df)
    if n < 3 or not pairs:
        return None
    t0 = time.perf_counter()
    overall: SearchHit | None = None
    best_pos: SearchHit | None = None
    best_vs_bh: SearchHit | None = None
    best_vs_peer: SearchHit | None = None
    trial_count = 0

    def _consider(cand: SearchHit) -> None:
        nonlocal overall, best_pos, best_vs_bh, best_vs_peer
        net = cand.net
        if overall is None or _better(cand, overall, direction):
            overall = cand
        if net > 0 and (best_pos is None or _better(cand, best_pos, direction)):
            best_pos = cand
        if (
            bh_net is not None
            and net > bh_net
            and (best_vs_bh is None or _better(cand, best_vs_bh, direction))
        ):
            best_vs_bh = cand
        peer_ok = peer_net is not None and net > peer_net
        fold_ok = cand.holdout_gate_ok is not False
        if peer_ok and fold_ok and (best_vs_peer is None or _better(cand, best_vs_peer, direction)):
            best_vs_peer = cand

    def _eval_pair(er: CompositeRule, xr: CompositeRule, family: str) -> None:
        nonlocal trial_count
        if time.perf_counter() - t0 > time_budget_s:
            return
        em = mask_conjuncts(cols, er.conjuncts)
        xm = mask_conjuncts(cols, xr.conjuncts)
        if not em.any() or not xm.any():
            return
        if (em.sum() / n) > _MAX_ENTRY_FRAC or (xm.sum() / n) > _MAX_EXIT_FRAC:
            return
        net = float("-inf")
        best_tsl = 0.0
        best_stats: dict[str, Any] | None = None
        train_net_v: float | None = None
        hold_net_v: float | None = None
        gate_ok: bool | None = None
        for tsl in (0.0, 0.02, 0.03, 0.05):
            trial_count += 1
            if train_indexes is not None:
                em_t = restrict_mask(em, train_indexes)
                xm_t = restrict_mask(xm, train_indexes)
                stats = simulate_long_with_fees(
                    df, em_t, xm_t, stake_usd=stake_usd, fee=fee, trailing_stop_pct=tsl
                )
            else:
                stats = simulate_long_with_fees(
                    df, em, xm, stake_usd=stake_usd, fee=fee, trailing_stop_pct=tsl
                )
            trades = int(stats.get("trades") or 0)
            if trades < _MIN_TRADES or trades > _MAX_TRADES:
                continue
            enriched = enrich_trial_stats(stats, stake_usd=stake_usd, bh_net=bh_net, n_bars=n)
            if enriched.get("reject_reason"):
                continue
            trial_net = float(stats.get("net_profit") or 0.0)
            if trial_net > net:
                net = trial_net
                best_tsl = float(tsl)
                best_stats = enriched
                train_net_v = trial_net
                if holdout_indexes:
                    em_h = restrict_mask(em, holdout_indexes)
                    xm_h = restrict_mask(xm, holdout_indexes)
                    hstats = simulate_long_with_fees(
                        df, em_h, xm_h, stake_usd=stake_usd, fee=fee, trailing_stop_pct=tsl
                    )
                    hold_net_v = float(hstats.get("net_profit") or 0.0)
                    gate_ok = passes_holdout_gate(train_net_v, hold_net_v)
                else:
                    hold_net_v = None
                    gate_ok = None
        if net == float("-inf") or best_stats is None:
            return
        _consider(
            SearchHit(
                er,
                xr,
                net,
                family,
                best_tsl,
                train_net=train_net_v,
                holdout_net=hold_net_v,
                holdout_gate_ok=gate_ok,
                fee_drag_pct=best_stats.get("fee_drag_pct"),
                exposure_pct=best_stats.get("exposure_pct"),
                excess_vs_bh=best_stats.get("excess_vs_bh"),
            )
        )

    primary = [(e, x, f) for e, x, f in pairs if f != "adaptive_exit"]
    adaptive = [(e, x, f) for e, x, f in pairs if f == "adaptive_exit"]
    for er, xr, family in primary + adaptive:
        _eval_pair(er, xr, family)
        if time.perf_counter() - t0 > time_budget_s:
            break

    champ = best_vs_peer or best_vs_bh or best_pos or overall
    if champ is not None and time.perf_counter() - t0 < time_budget_s:
        exit_pool: list[CompositeRule] = []
        seen_x: set[str] = set()
        for _e, xr, _fam in adaptive + pairs:
            sig = "|".join(f"{c.feature}{c.op}{c.value}" for c in xr.conjuncts)
            if sig in seen_x:
                continue
            seen_x.add(sig)
            exit_pool.append(xr)
            if len(exit_pool) >= 12:
                break
        for xr in exit_pool:
            if time.perf_counter() - t0 > time_budget_s:
                break
            _eval_pair(champ.entry, xr, "adaptive_exit")

    picked = best_vs_peer or best_vs_bh or best_pos or overall
    if picked is None:
        return None
    # SIM-08: attach null/stability badges on the winning recipe.
    from trendalgo.backtest.secret_sauce_lab.search_null import (  # noqa: PLC0415
        annotate_stability,
    )

    return annotate_stability(
        picked,
        df=df,
        cols=cols,
        fee=fee,
        stake_usd=stake_usd,
        trial_count=trial_count,
    )


def _better(cand: SearchHit, cur: SearchHit, direction: str | None) -> bool:
    """Higher excess-vs-BH wins when present; else Net %; Oracle families on ties."""
    if cand.excess_vs_bh is not None and cur.excess_vs_bh is not None:
        if cand.excess_vs_bh > cur.excess_vs_bh + 1e-12:
            return True
        if cand.excess_vs_bh < cur.excess_vs_bh - 1e-12:
            return False
    if cand.net > cur.net + 1e-12:
        return True
    if cand.net < cur.net - 1e-12:
        return False
    c_ok = cand.family in _ORACLE_FAM
    u_ok = cur.family in _ORACLE_FAM
    if c_ok and not u_ok:
        return True
    if u_ok and not c_ok:
        return False
    if direction == "down":
        pref = {"osc_cross", "peer_inspire", "mean_reversion", "oracle_pattern", "peer_pattern"}
        return cand.family in pref and cur.family not in pref
    return False


def bh_net_profit(df: pd.DataFrame, *, fee: Any, stake: float) -> float | None:
    try:
        from trendalgo.backtest.ta_fleet import buy_and_hold_row

        bh = buy_and_hold_row(df, lookback_seconds=0, stake_usd=stake, fee=fee)
        if bh is None:
            return None
        return float(bh.get("net_profit") or 0.0)
    except (TypeError, ValueError, KeyError):
        return None
