"""Build dossier + trial from a refine candidate."""

from __future__ import annotations

from typing import Any

from trendalgo.backtest.secret_sauce_dossier import HeartbeatDossier
from trendalgo.backtest.secret_sauce_features import entries_for_secret_sauce
from trendalgo.backtest.secret_sauce_lab.catalog_reseed import is_exact_peer_clone
from trendalgo.backtest.secret_sauce_lab.narrative import build_narrative
from trendalgo.backtest.secret_sauce_lab.refine_ladder import ladder_accepts
from trendalgo.backtest.secret_sauce_lab.regime_snapshot import RegimeSnapshot
from trendalgo.backtest.secret_sauce_lab.residual_instrument import build_residual_fields
from trendalgo.backtest.secret_sauce_lab.rsx_neighborhood import (
    is_rsx_neighborhood_rule,
    masks_for_rsx_rules,
)
from trendalgo.backtest.secret_sauce_lab.run import eval_lab_trial
from trendalgo.backtest.secret_sauce_lab.search import bh_net_profit


def pack_refine_candidate(
    best: tuple[Any, Any, float, str, str, Any, RegimeSnapshot],
    sauce: dict[str, Any],
    hints: list[dict[str, Any]],
    prior_net: float,
    peer_usd: float | None,
    fee: Any,
    stake: float,
    prior_tf: str,
) -> tuple[HeartbeatDossier, RegimeSnapshot, dict[str, Any], str] | None:
    entry_rule, exit_rule, search_net, family, search_tf, search_frame, regime = best
    bh_usd = bh_net_profit(search_frame, fee=fee, stake=stake)
    if not ladder_accepts(search_net, prior_net, peer_usd, bh_usd, search_tf == prior_tf):
        return None
    if is_exact_peer_clone(entry_rule, exit_rule, hints):
        return None
    formula, anti = build_narrative(
        regime,
        family=family,
        entry=entry_rule,
        exit_rule=exit_rule,
        beat_bh=bh_usd is not None and search_net > bh_usd,
    )
    anti += f" Inspired on {search_tf}; peer-class + mutated neighborhood — not a photocopy."
    raw_hb = sauce.get("heartbeat_dossier")
    hb0: dict[str, Any] = raw_hb if isinstance(raw_hb, dict) else {}
    swings = [int(i) for i in (hb0.get("oracle_entry_indexes") or [])]
    exits = [int(i) for i in (hb0.get("oracle_exit_indexes") or [])]
    if is_rsx_neighborhood_rule(entry_rule):
        packed = masks_for_rsx_rules(search_frame, entry_rule, exit_rule)
        if packed is None:
            return None
        entry_mask, exit_mask = packed
    else:
        entry_mask = entries_for_secret_sauce(search_frame, entry_rule)
        exit_mask = entries_for_secret_sauce(search_frame, exit_rule)
    swing_hits = tuple(bool(entry_mask[i]) for i in swings if 0 <= i < len(search_frame))
    exit_hits = tuple(bool(exit_mask[i]) for i in exits if 0 <= i < len(search_frame))
    residual = build_residual_fields(
        search_frame,
        entries=[i for i in swings if 0 <= i < len(search_frame)],
        exits=[i for i in exits if 0 <= i < len(search_frame)],
        swing_hits=swing_hits,
        exit_hits=exit_hits,
        sauce_net=search_net,
        oracle_net=None,
    )
    dossier = HeartbeatDossier(
        rule=entry_rule,
        exit_rule=exit_rule,
        formula_en=formula,
        train_coverage=float(hb0.get("train_coverage") or 0.0),
        holdout_coverage=float(hb0.get("holdout_coverage") or 0.0),
        swing_hits=swing_hits,
        exit_hits=exit_hits,
        oracle_entry_indexes=tuple(swings),
        oracle_exit_indexes=tuple(exits),
        anti_cheat=anti,
        residual_entry_indexes=residual["residual_entry_indexes"],
        residual_exit_indexes=residual["residual_exit_indexes"],
        residual_feature_hits=residual["residual_feature_hits"],
        oracle_gap_net_pct=residual["oracle_gap_net_pct"],
    )
    trial = eval_lab_trial(search_frame, dossier, fee=fee, stake_usd=stake, timeframe=search_tf)
    if trial is None:
        return None
    new_net = float(trial.get("net_profit") or 0.0)
    if not ladder_accepts(new_net, prior_net, peer_usd, bh_usd, search_tf == prior_tf):
        return None
    return dossier, regime, dict(trial), search_tf
