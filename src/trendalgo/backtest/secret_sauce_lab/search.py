"""Time-boxed fee-aware P&L search — maximize full-window Net % under peer/holdout filters."""

from __future__ import annotations

import math
import time
from typing import Any, NamedTuple

import pandas as pd

from trendalgo.backtest.oracle_pattern_mine import CompositeRule
from trendalgo.backtest.secret_sauce_lab.columnar import feature_matrix, mask_conjuncts
from trendalgo.backtest.secret_sauce_lab.search_folds import (
    passes_holdout_gate,
    passes_holdout_gate_soft,
    restrict_mask,
)
from trendalgo.backtest.secret_sauce_lab.search_metrics import enrich_trial_stats
from trendalgo.backtest.ta_simulator import simulate_long_with_fees
from trendalgo.exchanges.fees import ExchangeFeeSchedule

# Uncapped Sauce search (human opted to wait). Finite seed lists still bound work.
_TIME_BUDGET_S = float("inf")
_MAX_ENTRY_FRAC = 0.55
_MAX_EXIT_FRAC = 0.80
_MAX_TRADES = 200
_BUDGET_BASE_S = float("inf")
_BUDGET_HARD_CAP_S = float("inf")
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

# Gate tiers: hard preferred, then soft ladder, then ungated.
_GATE_HARD = 2
_GATE_SOFT = 1
_GATE_NONE = 0


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


def min_trades_for_oracle(n_oracle_swings: int) -> int:
    """Coverage floor vs Oracle swing count (rejects 1-trade luck when dense)."""
    n = max(0, int(n_oracle_swings))
    if n < 3:
        return 1
    # Cap at 8 so dense Oracles (50–100 swings) do not starve fee search.
    return min(8, max(3, int(math.ceil(0.15 * n))))


def lab_time_budget_s(n_oracle_swings: int, *, base_s: float = _BUDGET_BASE_S) -> float:
    """Sauce wall-clock is uncapped — return +inf (seed lists bound work)."""
    del n_oracle_swings, base_s
    return float("inf")


def _budget_done(t0: float, time_budget_s: float | None) -> bool:
    if time_budget_s is None or not math.isfinite(float(time_budget_s)):
        return False
    return time.perf_counter() - t0 > float(time_budget_s)


def search_best_pair(
    df: pd.DataFrame,
    pairs: list[tuple[CompositeRule, CompositeRule, str]],
    *,
    fee: ExchangeFeeSchedule,
    stake_usd: float,
    bh_net: float | None,
    time_budget_s: float | None = _TIME_BUDGET_S,
    peer_net: float | None = None,
    direction: str | None = None,
    train_indexes: list[int] | None = None,
    holdout_indexes: list[int] | None = None,
    purge_bars: int = 0,
    oracle_swing_count: int = 0,
    require_peer_clear: bool = False,
) -> SearchHit | None:
    """Return best SearchHit by full-window fee Net among holdout-ok (+ peer) candidates."""
    del purge_bars  # applied by caller when building indexes
    cols, _feats = feature_matrix(df)
    n = len(df)
    if n < 3 or not pairs:
        return None
    min_trades = min_trades_for_oracle(oracle_swing_count)
    # Train fold is shorter — only require ≥1 trade there; coverage floor is full-window.
    fold_min_trades = 1 if train_indexes is not None else min_trades
    t0 = time.perf_counter()
    # (er, xr, family, tsl, train, hold, gate_tier, stats)
    candidates: list[tuple[Any, ...]] = []
    trial_count = 0

    def _eval_pair(er: CompositeRule, xr: CompositeRule, family: str) -> None:
        nonlocal trial_count
        if _budget_done(t0, time_budget_s):
            return
        em = mask_conjuncts(cols, er.conjuncts)
        xm = mask_conjuncts(cols, xr.conjuncts)
        if not em.any() or not xm.any():
            return
        if (em.sum() / n) > _MAX_ENTRY_FRAC or (xm.sum() / n) > _MAX_EXIT_FRAC:
            return
        best_tsl = 0.0
        best_train = float("-inf")
        best_stats: dict[str, Any] | None = None
        train_net_v: float | None = None
        hold_net_v: float | None = None
        gate_tier = _GATE_NONE
        # L — deepen TSL 0–20% (1pp steps above 0, plus common seeds).
        for tsl in (
            0.0,
            0.01,
            0.02,
            0.03,
            0.04,
            0.05,
            0.06,
            0.08,
            0.10,
            0.12,
            0.15,
            0.18,
            0.20,
        ):
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
            if trades < fold_min_trades or trades > _MAX_TRADES:
                continue
            enriched = enrich_trial_stats(stats, stake_usd=stake_usd, bh_net=bh_net, n_bars=n)
            if enriched.get("reject_reason"):
                continue
            trial_net = float(stats.get("net_profit") or 0.0)
            if trial_net <= best_train:
                continue
            best_train = trial_net
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
                if passes_holdout_gate(train_net_v, hold_net_v):
                    gate_tier = _GATE_HARD
                elif passes_holdout_gate_soft(train_net_v, hold_net_v):
                    gate_tier = _GATE_SOFT
                else:
                    gate_tier = _GATE_NONE
            else:
                hold_net_v = None
                gate_tier = _GATE_NONE
        if best_stats is None or best_train == float("-inf"):
            return
        # Full-window fee re-sim for honest ranking + Oracle coverage floor.
        full = simulate_long_with_fees(
            df, em, xm, stake_usd=stake_usd, fee=fee, trailing_stop_pct=best_tsl
        )
        full_enriched = enrich_trial_stats(full, stake_usd=stake_usd, bh_net=bh_net, n_bars=n)
        if full_enriched.get("reject_reason"):
            return
        full_trades = int(full.get("trades") or 0)
        if full_trades < min_trades or full_trades > _MAX_TRADES:
            return
        full_net = float(full.get("net_profit") or 0.0)
        candidates.append(
            (
                er,
                xr,
                family,
                best_tsl,
                train_net_v,
                hold_net_v,
                gate_tier,
                {"net": full_net, **full_enriched},
            )
        )

    primary = [(e, x, f) for e, x, f in pairs if f != "adaptive_exit"]
    adaptive = [(e, x, f) for e, x, f in pairs if f == "adaptive_exit"]
    for er, xr, family in primary + adaptive:
        _eval_pair(er, xr, family)
        if _budget_done(t0, time_budget_s):
            break

    if candidates and not _budget_done(t0, time_budget_s):
        seed = max(candidates, key=lambda c: float(c[7]["net"]))
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
            if _budget_done(t0, time_budget_s):
                break
            _eval_pair(seed[0], xr, "adaptive_exit")

    picked = _pick_candidate(
        candidates,
        peer_net=peer_net,
        bh_net=bh_net,
        require_peer_clear=require_peer_clear,
        holdout_required=holdout_indexes is not None and len(holdout_indexes) > 0,
    )
    if picked is None:
        return None
    er, xr, family, tsl, train_n, hold_n, gate_tier, stats = picked
    gate_ok: bool | None
    if holdout_indexes:
        gate_ok = gate_tier >= _GATE_SOFT
    else:
        gate_ok = None
    hit = SearchHit(
        er,
        xr,
        float(stats["net"]),
        family,
        tsl,
        train_net=train_n,
        holdout_net=hold_n,
        holdout_gate_ok=gate_ok,
        fee_drag_pct=stats.get("fee_drag_pct"),
        exposure_pct=stats.get("exposure_pct"),
        excess_vs_bh=stats.get("excess_vs_bh"),
    )
    from trendalgo.backtest.secret_sauce_lab.search_null import annotate_stability  # noqa: PLC0415

    del direction
    return annotate_stability(
        hit,
        df=df,
        cols=cols,
        fee=fee,
        stake_usd=stake_usd,
        trial_count=trial_count,
    )


def _pick_candidate(
    candidates: list[Any],
    *,
    peer_net: float | None,
    bh_net: float | None,
    require_peer_clear: bool,
    holdout_required: bool,
) -> Any | None:
    """Maximize full-window net: hard holdout → soft → peer clear → net."""
    if not candidates:
        return None

    pool = list(candidates)
    if holdout_required:
        hard = [c for c in pool if int(c[6]) >= _GATE_HARD]
        soft = [c for c in pool if int(c[6]) >= _GATE_SOFT]
        if hard:
            pool = hard
        elif soft:
            pool = soft
        # else keep all — soft ladder empty; still rank by full net / peer

    def clears_peer(c: Any) -> bool:
        if peer_net is None:
            return True
        return float(c[7]["net"]) > peer_net

    peer_pool = [c for c in pool if clears_peer(c)]
    if require_peer_clear and peer_net is not None:
        if not peer_pool:
            return None
        pool = peer_pool
    elif peer_pool:
        pool = peer_pool

    def key(c: Any) -> tuple[float, float, int]:
        net = float(c[7]["net"])
        excess = float(c[7].get("excess_vs_bh") or (net - (bh_net or 0.0)))
        fam_bonus = 1 if c[2] in _ORACLE_FAM else 0
        return (net, excess, fam_bonus)

    return max(pool, key=key)


def _better(cand: SearchHit, cur: SearchHit, direction: str | None) -> bool:
    """Higher excess-vs-BH wins when present; else Net %; Oracle families on ties."""
    del direction
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
    return c_ok and not u_ok


def bh_net_profit(df: pd.DataFrame, *, fee: Any, stake: float) -> float | None:
    try:
        from trendalgo.backtest.ta_fleet import buy_and_hold_row

        bh = buy_and_hold_row(df, lookback_seconds=0, stake_usd=stake, fee=fee)
        if bh is None:
            return None
        return float(bh.get("net_profit") or 0.0)
    except (TypeError, ValueError, KeyError):
        return None
