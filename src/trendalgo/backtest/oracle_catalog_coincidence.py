"""Score catalog TA signals vs Oracle bars, then pick fee-aware entry×exit (Sauce TA)."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from trendalgo.backtest.fleet_config import PASS12_TRAILING_STOP_PCT
from trendalgo.backtest.oracle_pattern_mine import CompositeRule, RuleConjunct
from trendalgo.backtest.secret_sauce_dossier import HeartbeatDossier
from trendalgo.backtest.secret_sauce_lab.pattern_mine import indexes_from_trades
from trendalgo.backtest.ta_fleet import prepare_signals
from trendalgo.backtest.ta_simulator import simulate_long_with_fees

_SAUCE_TA = "Secret Sauce TA"
_SKIP = frozenset({"Oracle max", "B&H", "Secret Sauce", "Secret Sauce TA", "Secret Sauce Lab"})
_SID = "GEN_SECRET_1"
_TOP = 48
_PAIR = 12
_TSL = float(PASS12_TRAILING_STOP_PCT)

# Cached masks for one coincidence pass: sid -> (entries, exits, row, e_hit, x_hit)
_Cand = tuple[np.ndarray, np.ndarray, dict[str, Any], float, float]


def oracle_indexes_from_row(oracle: dict[str, Any], *, n: int) -> tuple[list[int], list[int]]:
    return indexes_from_trades(list(oracle.get("oracle_swings") or []), n=n)


def _win_rate_from_stats(stats: dict[str, Any]) -> float:
    raw = stats.get("win_rate")
    if raw is not None:
        try:
            return float(raw)
        except (TypeError, ValueError):
            pass
    trades = int(stats.get("trades") or 0)
    wins = int(stats.get("wins") or 0)
    open_n = int(stats.get("open_trades") or 0)
    closed = max(0, trades - open_n)
    if closed > 0:
        return wins / closed
    return (wins / trades) if trades > 0 else 0.0


def hit_rate(fires: np.ndarray, labels: list[int], *, window: int = 1) -> float:
    """Fraction of labels with a fire within ±window bars."""
    if not labels or fires.size == 0:
        return 0.0
    n = len(fires)
    hits = 0
    for i in labels:
        lo, hi = max(0, int(i) - window), min(n, int(i) + window + 1)
        if bool(np.any(fires[lo:hi])):
            hits += 1
    return hits / float(len(labels))


def _catalog_shortlist(
    catalog_rows: list[dict[str, Any]], *, timeframe: str
) -> list[dict[str, Any]]:
    return sorted(
        (
            r
            for r in catalog_rows
            if str(r.get("indicator") or "") not in _SKIP
            and str(r.get("timeframe") or "") in {"", timeframe}
        ),
        key=lambda r: float(r.get("net_pct") or float("-inf")),
        reverse=True,
    )[:_TOP]


def _build_candidates(
    df: pd.DataFrame,
    catalog_rows: list[dict[str, Any]],
    *,
    entry_labels: list[int],
    exit_labels: list[int],
    timeframe: str,
) -> dict[str, _Cand]:
    out: dict[str, _Cand] = {}
    for row in _catalog_shortlist(catalog_rows, timeframe=timeframe):
        sid = str(row.get("strategy_id") or row.get("indicator") or "")
        if not sid or sid in out:
            continue
        params = row.get("params") if isinstance(row.get("params"), dict) else {}
        entries, exits, _used = prepare_signals(df, sid, params)
        if entries is None or exits is None:
            continue
        e_arr = np.asarray(entries, dtype=bool)
        x_arr = np.asarray(exits, dtype=bool)
        out[sid] = (
            e_arr,
            x_arr,
            row,
            hit_rate(e_arr, entry_labels),
            hit_rate(x_arr, exit_labels),
        )
    return out


def score_catalog_vs_oracle(
    df: pd.DataFrame,
    catalog_rows: list[dict[str, Any]],
    *,
    entry_labels: list[int],
    exit_labels: list[int],
    timeframe: str,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Return (best_entry_row, best_exit_row) by coincidence hit-rate (shortlist helper)."""
    cands = _build_candidates(
        df,
        catalog_rows,
        entry_labels=entry_labels,
        exit_labels=exit_labels,
        timeframe=timeframe,
    )
    if not cands:
        return None, None
    best_e = max(cands.values(), key=lambda c: c[3])
    best_x = max(cands.values(), key=lambda c: c[4])
    return best_e[2], best_x[2]


def _pick_fee_aware_pair(
    df: pd.DataFrame,
    cands: dict[str, _Cand],
    *,
    fee: Any,
    stake: float,
) -> tuple[str, str, dict[str, Any]] | None:
    """Max fee-aware net among hit-rate + top-net shortlisted entry×exit combos."""
    if not cands:
        return None

    by_entry_hit = sorted(cands.items(), key=lambda kv: float(kv[1][3]), reverse=True)
    by_exit_hit = sorted(cands.items(), key=lambda kv: float(kv[1][4]), reverse=True)
    by_net = sorted(
        cands.items(),
        key=lambda kv: float(kv[1][2].get("net_pct") or float("-inf")),
        reverse=True,
    )
    # Hit-rate shortlist ∪ top catalog Net % (same TF) — still fee-aware objective.
    entry_sids = list(
        dict.fromkeys([sid for sid, _ in by_entry_hit[:_PAIR]] + [sid for sid, _ in by_net[:_PAIR]])
    )
    exit_sids = list(
        dict.fromkeys([sid for sid, _ in by_exit_hit[:_PAIR]] + [sid for sid, _ in by_net[:_PAIR]])
    )
    best_any: tuple[float, int, str, str, dict[str, Any]] | None = None
    best_floor: tuple[float, int, str, str, dict[str, Any]] | None = None
    for e_sid in entry_sids:
        entries = cands[e_sid][0]
        for x_sid in exit_sids:
            exits = cands[x_sid][1]
            stats = simulate_long_with_fees(
                df,
                entries,
                exits,
                stake_usd=stake,
                fee=fee,
                trailing_stop_pct=_TSL,
                collect_trades=False,
            )
            trades = int(stats.get("trades") or 0)
            if trades < 1:
                continue
            net = float(stats.get("net_profit") or 0.0)
            pack = (net, trades, e_sid, x_sid, stats)
            if best_any is None or net > best_any[0]:
                best_any = pack
            if trades >= 3 and (best_floor is None or net > best_floor[0]):
                best_floor = pack
    winner = best_floor if best_floor is not None else best_any
    if winner is None:
        return None
    net, _tr, e_sid, x_sid, stats = winner
    del net
    # Re-sim with trade list for dossier indexes.
    stats_full = simulate_long_with_fees(
        df,
        cands[e_sid][0],
        cands[x_sid][1],
        stake_usd=stake,
        fee=fee,
        trailing_stop_pct=_TSL,
        collect_trades=True,
    )
    return e_sid, x_sid, stats_full


def coincidence_sauce_row(
    df: pd.DataFrame,
    oracle: dict[str, Any],
    catalog_rows: list[dict[str, Any]],
    *,
    fee: Any,
    stake: float,
    symbol: str,
) -> dict[str, Any] | None:
    """Compose fee-aware best entry×exit catalog masks into a Secret Sauce TA row."""
    tf = str(oracle.get("timeframe") or "1h")
    e_lab, x_lab = oracle_indexes_from_row(oracle, n=len(df))
    if len(e_lab) < 2 or len(x_lab) < 1:
        return None
    cands = _build_candidates(df, catalog_rows, entry_labels=e_lab, exit_labels=x_lab, timeframe=tf)
    picked = _pick_fee_aware_pair(df, cands, fee=fee, stake=stake)
    if picked is None:
        return None
    e_sid, x_sid, stats = picked
    if int(stats.get("trades") or 0) < 1:
        return None
    entries = cands[e_sid][0]
    exits = cands[x_sid][1]
    from trendalgo.backtest.secret_sauce_pivot_gate import refine_masks_with_pivots

    entries, exits, stats, pivot_tag = refine_masks_with_pivots(
        df,
        entries,
        exits,
        entry_labels=e_lab,
        exit_labels=x_lab,
        fee=fee,
        stake=stake,
        trailing_stop_pct=_TSL,
    )
    te, tx = indexes_from_trades(list(stats.get("trade_list") or []), n=len(df))
    dossier = _dossier(e_sid, x_sid, e_lab, x_lab, te, tx, entries, exits)
    from trendalgo.backtest.hill_climb_tsl import assign_protective_tsl_from_masks
    from trendalgo.device.scanner_all_ta_prune import fleet_row_to_lts

    signal_net = float(stats.get("net_profit") or 0.0)
    tsl_pick = assign_protective_tsl_from_masks(
        df,
        entries,
        exits,
        fee=fee,
        stake=stake,
        signal_net=signal_net,
    )
    use = tsl_pick if tsl_pick is not None else stats
    hb = dossier.to_dict()
    params = {
        **dossier.eval_params(),
        "coincidence_entry": e_sid,
        "coincidence_exit": x_sid,
        "ss_ta_fee_aware": True,
    }
    if pivot_tag:
        params["pivot_gate"] = pivot_tag
    trial = {
        "strategy_id": _SID,
        "net_profit": float(use.get("net_profit") or 0.0),
        "gross_profit": float(use.get("gross_profit") or stats.get("gross_profit") or 0.0),
        "fees_paid": float(use.get("fees_paid") or stats.get("fees_paid") or 0.0),
        "trades": int(use.get("trades") or 0),
        "wins": int(use.get("wins") or 0),
        "open_trades": int(use.get("open_trades") or 0),
        "win_rate": _win_rate_from_stats(use if tsl_pick is not None else stats),
        "tsl_hits": int(use.get("tsl_hits") or 0),
        "trailing_stop_pct": float(use.get("trailing_stop_pct") or 0.0),
        "timeframe": tf,
        "bar_count": len(df),
        "heartbeat_dossier": hb,
        "params": params,
        "indicator": _SAUCE_TA,
        "ss_lab_pending": False,
        "ss_coincidence": True,
        "protective_tsl": bool(use.get("protective_tsl")),
        "tsl_breath": bool(use.get("tsl_breath")),
    }
    row = fleet_row_to_lts(trial, symbol=symbol, stake_usd=stake)
    row["indicator"] = _SAUCE_TA
    row["ss_lab_pending"] = False
    row["ss_coincidence"] = True
    row["heartbeat_dossier"] = hb
    return row


def _dossier(
    e_sid: str,
    x_sid: str,
    e_lab: list[int],
    x_lab: list[int],
    te: list[int],
    tx: list[int],
    entries: np.ndarray,
    exits: np.ndarray,
) -> HeartbeatDossier:
    rule = CompositeRule(
        strategy_id=_SID,
        conjuncts=(RuleConjunct("trough_confirm", ">=", 1.0),),
        rationale=f"fee-aware catalog entry≈{e_sid}",
    )
    exit_rule = CompositeRule(
        strategy_id=_SID,
        conjuncts=(RuleConjunct("peak_confirm", ">=", 1.0),),
        rationale=f"fee-aware catalog exit≈{x_sid}",
    )
    n = len(entries)
    swing_hits = tuple(bool(entries[i]) if 0 <= i < n else False for i in e_lab)
    exit_hits = tuple(bool(exits[i]) if 0 <= i < n else False for i in x_lab)
    return HeartbeatDossier(
        rule=rule,
        exit_rule=exit_rule,
        formula_en=(
            f"Enter≈{e_sid} at Oracle troughs; exit≈{x_sid} at Oracle peaks (fee-aware pair)."
        ),
        train_coverage=float(sum(swing_hits) / max(1, len(swing_hits))),
        holdout_coverage=float(sum(exit_hits) / max(1, len(exit_hits))),
        swing_hits=swing_hits,
        exit_hits=exit_hits,
        oracle_entry_indexes=tuple(e_lab),
        oracle_exit_indexes=tuple(x_lab),
        anti_cheat=(
            f"Catalog coincidence shortlist + fee-aware Net % (±1); not LLM. "
            f"e={len(te)} x={len(tx)}."
        ),
    )
