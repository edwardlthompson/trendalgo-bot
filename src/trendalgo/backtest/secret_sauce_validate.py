"""Independent Secret Sauce validation — re-simulate formula; no re-mine."""

from __future__ import annotations

import re
from typing import Any

import pandas as pd

from trendalgo.backtest.secret_sauce_dossier import HeartbeatDossier
from trendalgo.backtest.secret_sauce_features import ALL_FEATURE_KEYS, masks_for_secret_sauce
from trendalgo.backtest.ta_simulator import simulate_long_with_fees
from trendalgo.exchanges.fees import ExchangeFeeSchedule

_EPS = 0.05  # absolute Net % tolerance between trial and re-sim
_RSX_PERIOD = re.compile(r"^rsx\d+_x(?:up|dn)_\d+$")


def is_allowed_ss_feature(name: str) -> bool:
    """Static bank keys plus period-aware RSX neighborhood features."""
    if name in ALL_FEATURE_KEYS:
        return True
    return bool(_RSX_PERIOD.match(name))


def validate_secret_sauce(
    dossier: HeartbeatDossier,
    df: pd.DataFrame,
    trial_row: dict[str, Any],
    *,
    fee: ExchangeFeeSchedule,
    stake_usd: float,
    oracle_net: float,
    peer_net: float,
) -> tuple[bool, str]:
    """Return (ok, reason). Does not import mine fit logic."""
    for c in (*dossier.rule.conjuncts, *dossier.exit_rule.conjuncts):
        if c.feature and not is_allowed_ss_feature(c.feature):
            return False, f"unknown_feature:{c.feature}"
    entries, exits = masks_for_secret_sauce(
        df,
        entry_conjuncts=dossier.rule.conjuncts,
        exit_conjuncts=dossier.exit_rule.conjuncts,
    )
    if not entries.any():
        return False, "no_entries"
    stats = simulate_long_with_fees(
        df,
        entries,
        exits,
        stake_usd=stake_usd,
        fee=fee,
        trailing_stop_pct=0.0,
        collect_trades=False,
    )
    if stats["trades"] == 0:
        return False, "no_trades"
    re_profit = float(stats.get("net_profit") or 0.0)
    re_net = (re_profit / stake_usd) * 100.0 if stake_usd else 0.0
    trial_net = float(trial_row.get("net_pct") or 0.0)
    if abs(re_net - trial_net) > _EPS:
        return False, f"net_mismatch:{re_net:.4g}vs{trial_net:.4g}"
    if not (oracle_net > trial_net > peer_net):
        return False, "spectrum_fail"
    return True, "ok"
