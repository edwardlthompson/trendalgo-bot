"""Time-boxed fee-aware P&L search — maximize Net % toward Oracle ceiling."""

from __future__ import annotations

import time
from typing import Any

import pandas as pd

from trendalgo.backtest.oracle_pattern_mine import CompositeRule
from trendalgo.backtest.secret_sauce_lab.columnar import feature_matrix, mask_conjuncts
from trendalgo.backtest.ta_simulator import simulate_long_with_fees
from trendalgo.exchanges.fees import ExchangeFeeSchedule

_TIME_BUDGET_S = 4.0
_MAX_ENTRY_FRAC = 0.55
_MAX_EXIT_FRAC = 0.80
_MAX_TRADES = 200
# Families fitted on Oracle/peer bars — prefer at equal Net % (Oracle geometry).
_ORACLE_FAM = frozenset(
    {"oracle_pattern", "peer_pattern", "rsx_neighborhood", "osc_cross", "peer_reexpress"}
)


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
) -> tuple[CompositeRule, CompositeRule, float, str] | None:
    """Return best (entry, exit, net_profit, family).

    Objective: maximize fee Net % (Oracle is the unreachable ceiling).
    Constraint tiers: clear peer → clear B&H → positive → any. Never stop at
    a bare peer-clearer when a higher-Net recipe exists in the seed set.
    """
    cols, _feats = feature_matrix(df)
    n = len(df)
    if n < 3 or not pairs:
        return None
    t0 = time.perf_counter()
    overall: tuple[CompositeRule, CompositeRule, float, str] | None = None
    best_pos: tuple[CompositeRule, CompositeRule, float, str] | None = None
    best_vs_bh: tuple[CompositeRule, CompositeRule, float, str] | None = None
    best_vs_peer: tuple[CompositeRule, CompositeRule, float, str] | None = None
    for er, xr, family in pairs:
        if time.perf_counter() - t0 > time_budget_s:
            break
        em = mask_conjuncts(cols, er.conjuncts)
        xm = mask_conjuncts(cols, xr.conjuncts)
        if not em.any() or not xm.any():
            continue
        if (em.sum() / n) > _MAX_ENTRY_FRAC or (xm.sum() / n) > _MAX_EXIT_FRAC:
            continue
        # Small TSL grid — keep pair with best fee Net % (dossier still signal-first).
        net = float("-inf")
        for tsl in (0.0, 0.02, 0.03, 0.05):
            stats = simulate_long_with_fees(
                df, em, xm, stake_usd=stake_usd, fee=fee, trailing_stop_pct=tsl
            )
            trades = int(stats.get("trades") or 0)
            if trades < 1 or trades > _MAX_TRADES:
                continue
            trial_net = float(stats.get("net_profit") or 0.0)
            if trial_net > net:
                net = trial_net
        if net == float("-inf"):
            continue
        cand = (er, xr, net, family)
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
        if (
            peer_net is not None
            and net > peer_net
            and (best_vs_peer is None or _better(cand, best_vs_peer, direction))
        ):
            best_vs_peer = cand
    if best_vs_peer is not None:
        return best_vs_peer
    if best_vs_bh is not None:
        return best_vs_bh
    if best_pos is not None:
        return best_pos
    return overall


def _better(
    cand: tuple[CompositeRule, CompositeRule, float, str],
    cur: tuple[CompositeRule, CompositeRule, float, str],
    direction: str | None,
) -> bool:
    """Strictly higher Net % wins; at equal Net prefer Oracle-geometry families."""
    if cand[2] > cur[2] + 1e-12:
        return True
    if cand[2] < cur[2] - 1e-12:
        return False
    c_ok = cand[3] in _ORACLE_FAM
    u_ok = cur[3] in _ORACLE_FAM
    if c_ok and not u_ok:
        return True
    if u_ok and not c_ok:
        return False
    if direction == "down":
        pref = {"osc_cross", "peer_inspire", "mean_reversion", "oracle_pattern", "peer_pattern"}
        return cand[3] in pref and cur[3] not in pref
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
