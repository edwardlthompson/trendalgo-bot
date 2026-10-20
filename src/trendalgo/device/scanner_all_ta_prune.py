"""All-TA prune helpers: signal-only seeds, then deepen params + TSL."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pandas as pd

from trendalgo.backtest import hill_climb as _hill
from trendalgo.backtest.fleet_config import OPTIMIZE_TOP_N
from trendalgo.backtest.hill_climb import climb_seed
from trendalgo.backtest.hill_climb_axes import int_params
from trendalgo.exchanges.fees import ExchangeFeeSchedule, get_fee_schedule

ProgressFn = Callable[[str], None]
DEEPEN_TSL_PCTS = _hill.DEEPEN_TSL_PCTS


def fleet_row_to_lts(
    row: dict[str, Any],
    *,
    symbol: str,
    stake_usd: float,
    is_bh: bool = False,
    is_oracle: bool = False,
) -> dict[str, Any]:
    """Map a ta_fleet / simulator row into LTS Results / merge shape."""
    baseline = is_bh or is_oracle
    net = float(row.get("net_profit") or 0.0)
    stake = float(stake_usd) if stake_usd else 1.0
    net_pct = (net / stake) * 100.0
    fees_paid = float(row.get("fees_paid") or 0.0)
    # Prefer explicit percent, then win_rate fraction, then wins/(trades−open).
    # SS TA coincidence historically omitted win_rate and left win_pct as "-".
    win_pct: float | str
    existing = row.get("win_pct")
    if existing not in (None, "-", ""):
        try:
            win_pct = float(existing)
        except (TypeError, ValueError):
            win_pct = "-"
    else:
        win_pct = "-"
    if win_pct == "-":
        win_rate = row.get("win_rate")
        if win_rate is None:
            trades_n = int(row.get("trades") or 0)
            wins_n = int(row.get("wins") or 0)
            open_n = int(row.get("open_trades") or 0)
            closed = max(0, trades_n - open_n)
            if closed > 0:
                win_rate = wins_n / closed
            elif trades_n > 0:
                win_rate = wins_n / trades_n
        try:
            win_pct = float(win_rate) * 100.0 if win_rate is not None else "-"
        except (TypeError, ValueError):
            win_pct = "-"
    tsl = float(row.get("trailing_stop_pct") or 0.0)
    # Fraction (0.01) → percent (1); allow 0% for signal-only winners.
    tsl_pct = tsl * 100.0 if 0.0 < tsl <= 1.0 else tsl
    sid = str(row.get("strategy_id") or row.get("indicator") or "")
    ind0 = str(row.get("indicator") or "")
    is_secret = sid.upper().startswith("GEN_SECRET") or ind0.startswith("Secret Sauce")
    raw_params = dict(row.get("params") or {}) if not baseline else {}
    if is_secret:
        params = raw_params
    else:
        params = int_params(raw_params, sid) if raw_params else {}
    trades = row.get("trades")
    signal_net = row.get("signal_net_profit")
    if signal_net is None:
        signal_net = row.get("baseline_net_profit")
    try:
        signal_net_pct: float | None = (
            (float(signal_net) / stake) * 100.0 if signal_net is not None else net_pct
        )
    except (TypeError, ValueError):
        signal_net_pct = net_pct
    if is_oracle:
        indicator = "Oracle max"
    elif is_bh:
        indicator = "B&H"
    elif is_secret:
        # Preserve Secret Sauce TA / Lab labels when callers set them.
        indicator = ind0 if ind0.startswith("Secret Sauce") else "Secret Sauce Lab"
    else:
        indicator = sid
    out: dict[str, Any] = {
        "indicator": indicator,
        "timeframe": str(row.get("timeframe") or ""),
        "params": params,
        "trailing_stop_pct": None if baseline else float(tsl_pct),
        "trailing_stop_loss_pct": None if baseline else float(tsl_pct),
        "final_equity": stake + net,
        "net_pct": net_pct,
        "signal_net_pct": None if baseline else signal_net_pct,
        "gross_profit": float(row.get("gross_profit") or 0.0),
        "fees_paid": fees_paid,
        "fee_taker_pct": row.get("fee_taker_pct"),
        "stake_usd": stake,
        "trades": "-" if is_bh else int(trades or 0),
        "wins": "-" if is_bh else int(row.get("wins") or 0),
        "open_trades": 0 if baseline else int(row.get("open_trades") or 0),
        "win_pct": "-" if is_bh else win_pct,
        "tsl_hits": 0 if baseline else int(row.get("tsl_hits") or 0),
        "symbol": symbol,
        "optimized": bool(row.get("optimized")),
        "oracle_swings": list(row.get("oracle_swings") or row.get("trade_list") or [])
        if is_oracle
        else [],
    }
    dossier = row.get("heartbeat_dossier")
    if is_secret and isinstance(dossier, dict):
        out["heartbeat_dossier"] = dossier
        out["strategy_id"] = sid.upper() if sid else "GEN_SECRET_1"
    if is_secret and bool(row.get("ss_lab_pending")):
        out["ss_lab_pending"] = True
    regime = row.get("regime")
    if is_secret and isinstance(regime, dict):
        out["regime"] = regime
    if bool(row.get("protective_tsl")):
        out["protective_tsl"] = True
    if bool(row.get("tsl_breath")):
        out["tsl_breath"] = True
    return out


def is_profitable(row: dict[str, Any] | None) -> bool:
    """True when a fleet row has positive net profit."""
    if row is None:
        return False
    try:
        return float(row.get("net_profit") or 0.0) > 0.0
    except (TypeError, ValueError):
        return False


def select_bh_beaters(
    rows: list[dict[str, Any]],
    buy_hold: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """All positive-net rows that beat B&H (empty when B&H missing or none beat it)."""
    if buy_hold is None:
        return []
    try:
        bh_net = float(buy_hold.get("net_profit") or 0.0)
    except (TypeError, ValueError):
        return []
    beaters = [r for r in rows if is_profitable(r) and float(r.get("net_profit") or 0.0) > bh_net]
    return sorted(beaters, key=lambda r: float(r.get("net_profit") or 0.0), reverse=True)


def select_promising(
    rows: list[dict[str, Any]],
    buy_hold: dict[str, Any] | None,
    *,
    top_n: int = OPTIMIZE_TOP_N,
) -> list[dict[str, Any]]:
    """Legacy helper: B&H beaters first, else top positive; capped at top_n."""
    beaters = select_bh_beaters(rows, buy_hold)
    if beaters:
        return beaters[: max(0, int(top_n))]
    positive = [r for r in rows if is_profitable(r)]
    positive = sorted(positive, key=lambda r: float(r.get("net_profit") or 0.0), reverse=True)
    return positive[: max(0, int(top_n))]


def deepen_seeds(
    frame: pd.DataFrame,
    seeds: list[dict[str, Any]],
    *,
    fee: ExchangeFeeSchedule,
    stake_usd: float,
    timeframe: str,
    frames_by_tf: dict[str, pd.DataFrame] | None = None,
    on_progress: ProgressFn | None = None,
) -> list[dict[str, Any]]:
    """Params at signal-only, then TSL 1–20% for each seed on its own TF."""
    frames = dict(frames_by_tf or {})
    out: list[dict[str, Any]] = []
    for seed in seeds:
        tf = str(seed.get("timeframe") or timeframe)
        active = frames.get(tf, frame)
        best = climb_seed(
            active,
            seed,
            fee=fee,
            stake_usd=stake_usd,
            timeframe=tf,
            frames_by_tf=frames,
            on_progress=on_progress,
        )
        if best is not None:
            out.append(best)
    return out


def fee_for_bps(fee_bps_round_trip: float) -> ExchangeFeeSchedule:
    return fee_for_exchange("kraken", fee_bps_round_trip)


def fee_for_exchange(
    exchange_id: str,
    fee_bps_round_trip: float | None = None,
) -> ExchangeFeeSchedule:
    """Prefer stored exchange schedule; fall back to round-trip bps."""
    eid = (exchange_id or "kraken").strip().lower() or "kraken"
    try:
        return get_fee_schedule(eid)
    except KeyError:
        bps = 52.0 if fee_bps_round_trip is None else float(fee_bps_round_trip)
        taker = max(0.0, bps / 10_000.0 / 2.0)
        return ExchangeFeeSchedule(
            exchange_id=eid,
            taker_pct=taker,
            maker_pct=taker,
            tier="fallback",
            source_url="",
            source="bps",
        )
