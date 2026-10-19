"""Last-chance fat family search to clear absolute peer Net %."""

from __future__ import annotations

from typing import Any

from trendalgo.backtest.secret_sauce_dossier import dossier_from_dict
from trendalgo.backtest.secret_sauce_lab.catalog_reseed import is_exact_peer_clone
from trendalgo.backtest.secret_sauce_lab.families import seeds_for_weights
from trendalgo.backtest.secret_sauce_lab.peer_inspire import inspire_seeds_for_hints
from trendalgo.backtest.secret_sauce_lab.regime_snapshot import detect_regime
from trendalgo.backtest.secret_sauce_lab.search import bh_net_profit, search_best_pair

_SID = "GEN_SECRET_1"
_FAT = {
    "dip_uptrend": 1.0,
    "mean_reversion": 1.0,
    "osc_cross": 1.0,
    "momentum": 1.0,
    "squeeze_breakout": 0.5,
    "volume_impulse": 0.5,
}


def fat_beat_peer(
    sauce: dict[str, Any],
    frame: Any,
    search_tf: str,
    hints: list[dict[str, Any]],
    peer_usd: float,
    fee: Any,
    stake: float,
    out: list[Any],
) -> None:
    seeds = [(er, xr, "peer_fat") for er, xr, _f in seeds_for_weights(_SID, _FAT, volume_ok=True)]
    if hints:
        seeds = inspire_seeds_for_hints(_SID, hints) + seeds
    prior = dossier_from_dict(sauce.get("heartbeat_dossier"))
    if prior is not None:
        seeds = [(prior.rule, prior.exit_rule, "first_pass")] + seeds
    regime = detect_regime(frame)
    bh_usd = bh_net_profit(frame, fee=fee, stake=stake)
    picked = search_best_pair(
        frame,
        seeds,
        fee=fee,
        stake_usd=stake,
        bh_net=bh_usd,
        time_budget_s=3.0,
        peer_net=peer_usd,
        direction=regime.direction,
    )
    if (
        picked is not None
        and picked[2] > peer_usd
        and not is_exact_peer_clone(picked[0], picked[1], hints)
    ):
        er, xr, net, fam = picked
        out.append((er, xr, net, fam, search_tf, frame, regime))
