"""Shared helper → Results row packing."""

from __future__ import annotations

from typing import Any

from trendalgo.backtest.secret_sauce_dossier import HeartbeatDossier
from trendalgo.backtest.secret_sauce_lab.regime_snapshot import RegimeSnapshot
from trendalgo.backtest.secret_sauce_lab.run import eval_lab_trial
from trendalgo.device.scanner_all_ta_prune import fleet_row_to_lts
from trendalgo.exchanges.fees import ExchangeFeeSchedule


def pack_helper_row(
    dossier: HeartbeatDossier,
    regime: RegimeSnapshot,
    frame: Any,
    *,
    fee: ExchangeFeeSchedule,
    stake: float,
    symbol: str,
    timeframe: str,
    indicator: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    trial = eval_lab_trial(frame, dossier, fee=fee, stake_usd=stake, timeframe=timeframe)
    if trial is None:
        return None
    hb = dossier.to_dict()
    hb["regime"] = regime.to_dict()
    if extra:
        hb.update(extra)
    trial["timeframe"] = timeframe
    trial["heartbeat_dossier"] = hb
    trial["params"] = {**dossier.eval_params(), "regime": regime.to_dict()}
    trial["indicator"] = indicator
    trial["strategy_id"] = dossier.rule.strategy_id
    trial["ss_lab_pending"] = False
    trial["regime"] = regime.to_dict()
    row = fleet_row_to_lts(trial, symbol=symbol, stake_usd=stake)
    row["indicator"] = indicator
    row["ss_lab_pending"] = False
    row["regime"] = regime.to_dict()
    if isinstance(row.get("heartbeat_dossier"), dict):
        row["heartbeat_dossier"] = {**row["heartbeat_dossier"], "regime": regime.to_dict()}
    return row
