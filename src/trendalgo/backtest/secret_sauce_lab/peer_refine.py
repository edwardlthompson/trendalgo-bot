"""Second-pass refine — Oracle-first fee max; peer Net % is validation floor only."""

from __future__ import annotations

from typing import Any

from trendalgo.backtest.secret_sauce_dossier import dossier_from_dict
from trendalgo.backtest.secret_sauce_lab.catalog_reseed import (
    absolute_max_peer_net,
    is_exact_peer_clone,
    peer_hints_from_rows,
)
from trendalgo.backtest.secret_sauce_lab.families import seeds_for_weights
from trendalgo.backtest.secret_sauce_lab.fat_beat import fat_beat_peer
from trendalgo.backtest.secret_sauce_lab.pattern_mine import pattern_seed_pairs
from trendalgo.backtest.secret_sauce_lab.peer_inspire import should_run_rsx_neighborhood
from trendalgo.backtest.secret_sauce_lab.peer_trade_bars import (
    pattern_and_inspire_seeds,
    rsx_seed_from_peer,
    top_peer_row,
)
from trendalgo.backtest.secret_sauce_lab.refine_ladder import (
    peer_tf_for_indicator,
    refine_tf_budgets,
    refine_tf_candidates,
)
from trendalgo.backtest.secret_sauce_lab.refine_pack import pack_refine_candidate
from trendalgo.backtest.secret_sauce_lab.regime_snapshot import RegimeSnapshot, detect_regime
from trendalgo.backtest.secret_sauce_lab.rsx_neighborhood import search_rsx_neighborhood
from trendalgo.backtest.secret_sauce_lab.search import bh_net_profit, search_best_pair

_SID = "GEN_SECRET_1"


def refine_lab_from_peers(
    sauce: dict[str, Any],
    rows: list[dict[str, Any]],
    frame: Any,
    *,
    stake: float,
    fee: Any,
    time_budget_s: float = 12.0,
    frames_by_tf: dict[str, Any] | None = None,
) -> tuple[Any, RegimeSnapshot, dict[str, Any], str] | None:
    """Oracle-directed refine; peer peek only as last-resort skim under peer bar."""
    tf = str(sauce.get("timeframe") or "1h")
    inspire_hints = peer_hints_from_rows(rows, preferred_tf="", prefer_osc=True)
    if not inspire_hints:
        inspire_hints = peer_hints_from_rows(
            rows, preferred_tf="", prefer_osc=True, require_beat_bh=False
        )
    abs_pct = absolute_max_peer_net(rows, preferred_tf="")
    peer_usd = (abs_pct / 100.0) * stake if abs_pct is not None else None
    prior_net = float(sauce.get("net_profit") or 0.0)
    abs_hints = peer_hints_from_rows(rows, preferred_tf="", prefer_osc=False, require_beat_bh=False)
    top_abs = abs_hints[0] if abs_hints else (inspire_hints[0] if inspire_hints else None)
    peer_tf = peer_tf_for_indicator(rows, str(top_abs["indicator"])) if top_abs else None
    peer_row = top_peer_row(rows)
    seed_peer = rsx_seed_from_peer(peer_row) or next(
        (h for h in inspire_hints if should_run_rsx_neighborhood([h])), None
    )
    candidates: list[tuple[Any, Any, float, str, str, Any, RegimeSnapshot]] = []
    tf_list = refine_tf_candidates(peer_tf, tf)
    for search_tf, budget in zip(
        tf_list, refine_tf_budgets(len(tf_list), time_budget_s), strict=False
    ):
        search_frame = frame
        if frames_by_tf and frames_by_tf.get(search_tf) is not None:
            search_frame = frames_by_tf[search_tf]
        elif search_tf != tf:
            continue
        _search_tf_oracle_first(
            sauce,
            search_frame,
            search_tf,
            inspire_hints,
            seed_peer,
            peer_row,
            peer_usd,
            fee,
            stake,
            budget,
            candidates,
        )
    # Last resort: RSX clear + fat + peer-pattern skim if still under peer.
    if peer_usd is not None and (not candidates or max(c[2] for c in candidates) <= peer_usd):
        clear_tf = peer_tf or tf
        clear_frame = (
            frames_by_tf.get(clear_tf)
            if frames_by_tf and frames_by_tf.get(clear_tf) is not None
            else frame
        )
        if seed_peer is not None:
            _rsx_clear_fallback(
                clear_frame,
                clear_tf,
                seed_peer,
                peer_usd,
                fee,
                stake,
                candidates,
            )
        if peer_tf and frames_by_tf and frames_by_tf.get(peer_tf) is not None:
            fat_beat_peer(
                sauce,
                frames_by_tf[peer_tf],
                peer_tf,
                inspire_hints,
                peer_usd,
                fee,
                stake,
                candidates,
            )
        if not candidates or max(c[2] for c in candidates) <= peer_usd:
            _peer_skim_fallback(
                sauce, frame, tf, inspire_hints, peer_row, peer_usd, fee, stake, candidates
            )
    if not candidates:
        return None
    return pack_refine_candidate(
        max(candidates, key=lambda c: c[2]),
        sauce,
        inspire_hints,
        prior_net,
        peer_usd,
        fee,
        stake,
        tf,
    )


def _search_tf_oracle_first(
    sauce: dict[str, Any],
    search_frame: Any,
    search_tf: str,
    hints: list[dict[str, Any]],
    seed_peer: dict[str, Any] | None,
    peer_row: dict[str, Any] | None,
    peer_usd: float | None,
    fee: Any,
    stake: float,
    budget: float,
    out: list[tuple[Any, Any, float, str, str, Any, RegimeSnapshot]],
) -> None:
    """Primary brain: oracle pattern + regime families (+ default osc RSX grid)."""
    del peer_row  # unused — peer peek is last-resort only
    bh_usd = bh_net_profit(search_frame, fee=fee, stake=stake)
    regime = detect_regime(search_frame)
    seeds: list[tuple[Any, Any, str]] = []
    prior = dossier_from_dict(sauce.get("heartbeat_dossier"))
    if prior is not None and str(sauce.get("timeframe") or "") == search_tf:
        seeds.append((prior.rule, prior.exit_rule, "first_pass"))
    # Re-mine Oracle geometry on this TF when dossier carries swing indexes.
    if prior is not None:
        e_idx = list(prior.oracle_entry_indexes)
        x_idx = list(prior.oracle_exit_indexes)
        if len(e_idx) >= 2 and len(x_idx) >= 1:
            seeds.extend(
                pattern_seed_pairs(
                    search_frame,
                    entry_indexes=e_idx,
                    exit_indexes=x_idx,
                    strategy_id=_SID,
                    family="oracle_pattern",
                    fee=fee,
                    stake_usd=stake,
                    time_budget_s=max(0.5, budget * 0.25),
                )
            )
    seeds.extend(seeds_for_weights(_SID, regime.family_weights, volume_ok=regime.volume_ok))
    picked = search_best_pair(
        search_frame,
        seeds,
        fee=fee,
        stake_usd=stake,
        bh_net=bh_usd,
        time_budget_s=max(0.6, budget * 0.7),
        peer_net=peer_usd,
        direction=regime.direction,
    )
    if picked is not None and not is_exact_peer_clone(picked[0], picked[1], hints):
        er, xr, net, fam = picked
        out.append((er, xr, net, fam, search_tf, search_frame, regime))
    # Default osc neighborhood (not peer-anchored levels) when still thin.
    if seed_peer is not None and (not out or (peer_usd is not None and out[-1][2] <= peer_usd)):
        rsx_hit = search_rsx_neighborhood(
            search_frame,
            fee=fee,
            stake_usd=stake,
            peer_entry=float(seed_peer.get("entry_level") or 30),
            peer_exit=float(seed_peer.get("exit_level") or 70),
            peer_period=int(seed_peer.get("period") or 14),
            peer_net_usd=peer_usd,
            strategy_id=_SID,
            time_budget_s=max(1.0, budget * 0.35),
        )
        if rsx_hit is not None:
            er, xr, net, fam = rsx_hit
            out.append((er, xr, net, fam, search_tf, search_frame, regime))


def _rsx_clear_fallback(
    frame: Any,
    tf: str,
    seed_peer: dict[str, Any],
    peer_usd: float,
    fee: Any,
    stake: float,
    out: list[tuple[Any, Any, float, str, str, Any, RegimeSnapshot]],
) -> None:
    """Dedicated cross-period RSX hunt when Oracle-first left Sauce under peer."""
    regime = detect_regime(frame)
    rsx_hit = search_rsx_neighborhood(
        frame,
        fee=fee,
        stake_usd=stake,
        peer_entry=float(seed_peer.get("entry_level") or 30),
        peer_exit=float(seed_peer.get("exit_level") or 70),
        peer_period=int(seed_peer.get("period") or 14),
        peer_net_usd=peer_usd,
        strategy_id=_SID,
        time_budget_s=4.0,
    )
    if rsx_hit is not None and rsx_hit[2] > peer_usd:
        er, xr, net, fam = rsx_hit
        out.append((er, xr, net, fam, tf, frame, regime))


def _peer_skim_fallback(
    sauce: dict[str, Any],
    frame: Any,
    tf: str,
    hints: list[dict[str, Any]],
    peer_row: dict[str, Any] | None,
    peer_usd: float | None,
    fee: Any,
    stake: float,
    out: list[tuple[Any, Any, float, str, str, Any, RegimeSnapshot]],
) -> None:
    """Short peer-pattern skim only when Oracle-first failed to clear peer."""
    bh_usd = bh_net_profit(frame, fee=fee, stake=stake)
    regime = detect_regime(frame)
    seeds = pattern_and_inspire_seeds(frame, tf, hints, peer_row, fee, stake)
    picked = search_best_pair(
        frame,
        seeds,
        fee=fee,
        stake_usd=stake,
        bh_net=bh_usd,
        time_budget_s=2.0,
        peer_net=peer_usd,
        direction=regime.direction,
    )
    if picked is not None and not is_exact_peer_clone(picked[0], picked[1], hints):
        er, xr, net, fam = picked
        out.append((er, xr, net, fam, tf, frame, regime))
