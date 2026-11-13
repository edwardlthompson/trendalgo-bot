"""V — meta-TSL: pick best trailing stop among helper rows via fee re-grid."""

from __future__ import annotations

from typing import Any

import pandas as pd

from trendalgo.backtest.secret_sauce_dossier import dossier_from_dict
from trendalgo.backtest.secret_sauce_features import entries_for_secret_sauce
from trendalgo.backtest.ta_simulator import simulate_long_with_fees
from trendalgo.exchanges.fees import ExchangeFeeSchedule

_TSL_GRID = (0.0, 0.01, 0.02, 0.03, 0.05, 0.08, 0.10, 0.12, 0.15, 0.20)


def best_tsl_for_row(
    df: pd.DataFrame,
    row: dict[str, Any],
    *,
    fee: ExchangeFeeSchedule,
    stake_usd: float,
) -> tuple[float, float]:
    """Return (best_tsl_fraction, best_net)."""
    d = dossier_from_dict(row.get("heartbeat_dossier"))
    if d is None or df.empty:
        return 0.0, float(row.get("net_profit") or 0.0)
    em = entries_for_secret_sauce(df, d.rule)
    xm = entries_for_secret_sauce(df, d.exit_rule)
    best_tsl = float(d.trailing_stop_pct or 0.0)
    best_net = float("-inf")
    for tsl in _TSL_GRID:
        stats = simulate_long_with_fees(
            df, em, xm, stake_usd=stake_usd, fee=fee, trailing_stop_pct=float(tsl)
        )
        net = float(stats.get("net_profit") or 0.0)
        if net > best_net:
            best_net = net
            best_tsl = float(tsl)
    return best_tsl, best_net


def apply_meta_tsl_to_helpers(
    df: pd.DataFrame,
    helper_rows: list[dict[str, Any]],
    *,
    fee: ExchangeFeeSchedule,
    stake_usd: float,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in helper_rows:
        tsl, net = best_tsl_for_row(df, row, fee=fee, stake_usd=stake_usd)
        upd = dict(row)
        upd["trailing_stop_pct"] = tsl
        upd["trailing_stop_loss_pct"] = tsl
        if stake_usd:
            upd["net_pct"] = round(net / stake_usd * 100.0, 4)
        hb = dict(upd.get("heartbeat_dossier") or {})
        hb["trailing_stop_pct"] = tsl
        upd["heartbeat_dossier"] = hb
        params = dict(upd.get("params") or {})
        params["trailing_stop_pct"] = tsl
        upd["params"] = params
        out.append(upd)
    return out
