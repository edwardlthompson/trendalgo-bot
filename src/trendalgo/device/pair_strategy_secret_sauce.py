"""Secret Sauce TA / Lab hooks for All-TA pair scan (pending → upsert)."""

from __future__ import annotations

from typing import Any

from trendalgo.device.sauce_names import SAUCE_ALL, SAUCE_LAB, SAUCE_LEGACY, SAUCE_TA, is_sauce_lab
from trendalgo.device.scanner_all_ta_prune import fleet_row_to_lts

_BH = "B&H"


def best_oracle_row(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    oracle_rows = [r for r in rows if str(r.get("indicator") or "") == "Oracle max"]
    if not oracle_rows:
        return None
    return max(oracle_rows, key=lambda r: float(r.get("net_pct") or float("-inf")))


def lab_oracle_row(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Prefer 1h Oracle for Lab (densest bars); else best Oracle Net %."""
    ones = [
        r
        for r in rows
        if str(r.get("indicator") or "") == "Oracle max" and str(r.get("timeframe") or "") == "1h"
    ]
    if ones:
        return max(ones, key=lambda r: float(r.get("net_pct") or float("-inf")))
    return best_oracle_row(rows)


def pending_sauce_row(*, symbol: str, timeframe: str, stake: float) -> dict[str, Any]:
    """Placeholder so Results can show Secret Sauce Lab while it cooks."""
    trial = {
        "strategy_id": "GEN_SECRET_1",
        "indicator": SAUCE_LAB,
        "timeframe": timeframe,
        "net_profit": 0.0,
        "gross_profit": 0.0,
        "fees_paid": 0.0,
        "trades": 0,
        "wins": 0,
        "params": {"status": "computing"},
        "ss_lab_pending": True,
        "phase": "sauce",
    }
    row = fleet_row_to_lts(trial, symbol=symbol, stake_usd=stake)
    row["indicator"] = SAUCE_LAB
    row["ss_lab_pending"] = True
    row["net_pct"] = None
    row["params"] = {"status": "computing"}
    return row


def upsert_sauce_named(
    rows: list[dict[str, Any]],
    sauce: dict[str, Any],
    *,
    name: str,
) -> list[dict[str, Any]]:
    """Replace pending/prior row matching ``name`` (and legacy Lab alias)."""
    aliases = {name}
    if name == SAUCE_LAB:
        aliases.add(SAUCE_LEGACY)
    tf = str(sauce.get("timeframe") or "")
    sauce = dict(sauce)
    sauce["indicator"] = name
    out: list[dict[str, Any]] = []
    replaced = False
    for r in rows:
        ind = str(r.get("indicator") or "")
        if ind not in aliases:
            out.append(r)
            continue
        r_tf = str(r.get("timeframe") or "")
        pending = bool(r.get("ss_lab_pending"))
        same_tf = (not tf) or (r_tf == tf)
        if not replaced and (pending or same_tf):
            out.append(sauce)
            replaced = True
            continue
        if pending:
            continue
        out.append(r)
    if not replaced:
        out.append(sauce)
    return out


def upsert_secret_sauce(rows: list[dict[str, Any]], sauce: dict[str, Any]) -> list[dict[str, Any]]:
    """Upsert Lab row (legacy helper name)."""
    return upsert_sauce_named(rows, sauce, name=SAUCE_LAB)


def upsert_secret_sauce_ta(
    rows: list[dict[str, Any]], sauce: dict[str, Any]
) -> list[dict[str, Any]]:
    return upsert_sauce_named(rows, sauce, name=SAUCE_TA)


def mine_and_eval_secret_sauce(
    oracle: dict[str, Any],
    *,
    frames_by_tf: dict[str, Any],
    symbol: str,
    stake: float,
    fee: Any,
) -> dict[str, Any] | None:
    """Background worker: multi-TF Lab keep-best then backtest_one (soft-fail)."""
    from trendalgo.backtest.secret_sauce_lab.multi_tf_lab import mine_best_across_tfs

    swings = list(oracle.get("oracle_swings") or [])
    tf = str(oracle.get("timeframe") or "1h")
    if frames_by_tf.get(tf) is None or not swings:
        return None
    try:
        packed = mine_best_across_tfs(
            frames_by_tf,
            oracle_tf=tf,
            oracle_trades=swings,
            fee=fee,
            stake_usd=stake,
            time_budget_s=6.0,
        )
    except (TypeError, ValueError, KeyError, IndexError):
        return None
    if packed is None:
        return None
    dossier, regime, trial, out_tf = packed
    hb = dossier.to_dict()
    hb["regime"] = regime.to_dict()
    trial["timeframe"] = out_tf
    trial["heartbeat_dossier"] = hb
    trial["params"] = {**dossier.eval_params(), "regime": regime.to_dict()}
    trial["indicator"] = SAUCE_LAB
    trial["strategy_id"] = dossier.rule.strategy_id
    trial["ss_lab_pending"] = False
    trial["regime"] = regime.to_dict()
    row = fleet_row_to_lts(trial, symbol=symbol, stake_usd=stake)
    row["indicator"] = SAUCE_LAB
    row["ss_lab_pending"] = False
    row["regime"] = regime.to_dict()
    if isinstance(row.get("heartbeat_dossier"), dict):
        row["heartbeat_dossier"] = {**row["heartbeat_dossier"], "regime": regime.to_dict()}
    return row


def refine_sauce_from_peers(
    sauce: dict[str, Any],
    rows: list[dict[str, Any]],
    frames_by_tf: dict[str, Any],
    *,
    stake: float,
    fee: Any,
    time_budget_s: float = 12.0,
) -> dict[str, Any]:
    """Second-pass Lab refine: maximize fee Net % toward Oracle; peer clear is floor."""
    from trendalgo.backtest.secret_sauce_lab.peer_refine import refine_lab_from_peers

    tf = str(sauce.get("timeframe") or "1h")
    frame = frames_by_tf.get(tf)
    if frame is None:
        return sauce
    packed = refine_lab_from_peers(
        sauce,
        rows,
        frame,
        stake=stake,
        fee=fee,
        time_budget_s=time_budget_s,
        frames_by_tf=frames_by_tf,
    )
    if packed is None:
        out = dict(sauce)
        out["indicator"] = SAUCE_LAB
        return out
    dossier, regime, trial, out_tf = packed
    hb = dossier.to_dict()
    hb["regime"] = regime.to_dict()
    trial["timeframe"] = out_tf
    trial["heartbeat_dossier"] = hb
    trial["params"] = {**dossier.eval_params(), "regime": regime.to_dict()}
    trial["indicator"] = SAUCE_LAB
    trial["strategy_id"] = dossier.rule.strategy_id
    trial["ss_lab_pending"] = False
    trial["regime"] = regime.to_dict()
    trial["ss_peer_reseed"] = True
    row = fleet_row_to_lts(trial, symbol=str(sauce.get("symbol") or ""), stake_usd=stake)
    row["indicator"] = SAUCE_LAB
    row["ss_lab_pending"] = False
    row["regime"] = regime.to_dict()
    row["ss_peer_reseed"] = True
    if isinstance(row.get("heartbeat_dossier"), dict):
        row["heartbeat_dossier"] = {**row["heartbeat_dossier"], "regime": regime.to_dict()}
    return row


def validate_sauce_against_peers(
    sauce: dict[str, Any],
    rows: list[dict[str, Any]],
    frames_by_tf: dict[str, Any],
    *,
    stake: float,
    fee: Any,
) -> tuple[bool, str]:
    from trendalgo.backtest.secret_sauce_dossier import dossier_from_dict
    from trendalgo.backtest.secret_sauce_validate import validate_secret_sauce

    if bool(sauce.get("ss_lab_pending")):
        return False, "lab_pending"
    dossier = dossier_from_dict(sauce.get("heartbeat_dossier"))
    if dossier is None:
        return False, "no_dossier"
    tf = str(sauce.get("timeframe") or "1h")
    frame = frames_by_tf.get(tf)
    if frame is None:
        return False, "no_frame"
    oracle_net = float((best_oracle_row(rows) or {}).get("net_pct") or 0.0)
    peer = float("-inf")
    for r in rows:
        name = str(r.get("indicator") or "")
        if name in SAUCE_ALL or name == "Oracle max":
            continue
        if name == _BH:
            peer = max(peer, float(r.get("net_pct") or float("-inf")))
            continue
        peer = max(peer, float(r.get("net_pct") or float("-inf")))
    if peer == float("-inf"):
        peer = _best_bh_net(rows)
    return validate_secret_sauce(
        dossier,
        frame,
        sauce,
        fee=fee,
        stake_usd=stake,
        oracle_net=oracle_net,
        peer_net=peer,
    )


def _best_bh_net(rows: list[dict[str, Any]]) -> float:
    best = float("-inf")
    for r in rows:
        if str(r.get("indicator") or "") == _BH:
            best = max(best, float(r.get("net_pct") or float("-inf")))
    return best if best != float("-inf") else 0.0


def current_lab_sauce(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    sauces = [r for r in rows if is_sauce_lab(r.get("indicator")) and not r.get("ss_lab_pending")]
    if not sauces:
        return None
    return max(sauces, key=lambda r: float(r.get("net_pct") or float("-inf")))
