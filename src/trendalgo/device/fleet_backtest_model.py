"""Fleet backtest helpers for the device app (parity-fleet-backtest).

Device runs pass 1 only (strategy × timeframe sweep). Pass 2 (param optimize) and pass 3 (TSL sweep)
stay in ``fleet_runner`` for the API host; the device job passes ``max_passes=1``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from trendalgo.backtest.fleet_runner import FleetPreflightError, validate_fleet_request
from trendalgo.constants.timeframes import TRADINGVIEW_INTERVAL_LABELS
from trendalgo.device.fields import LIVE_V1_INDICATORS, TIMEFRAMES, check_pair, parse_number
from trendalgo.device.profile import shared_data_dir

DEFAULT_EXCHANGE = "kraken"
DEFAULT_STAKE_USD = 1000.0
STAKE_MAX_USD = 1_000_000.0


class FleetBacktestError(RuntimeError):
    """Preflight or runtime failure the page can show."""


@dataclass(frozen=True)
class FleetBacktestRequest:
    exchange_id: str
    pair: str
    stake_usd: float


def fleet_data_dir(profile_root: Path) -> Path:
    """OHLCV and fleet store folder (shared API data dir when set)."""
    return shared_data_dir() or profile_root


def validate_fleet_backtest(
    *,
    exchange_id: str,
    pair: str,
    stake: str,
) -> tuple[FleetBacktestRequest | None, list[str]]:
    errors: list[str] = []
    eid = exchange_id.strip().lower() or DEFAULT_EXCHANGE
    symbol = check_pair(pair)
    if symbol is None:
        errors.append("Pair: use BASE/QUOTE, for example BTC/USD.")
    amount = parse_number(stake)
    if amount is None or not 0 < amount <= STAKE_MAX_USD:
        errors.append(f"Stake: enter a USD amount above 0, up to {STAKE_MAX_USD:,.0f}.")
    if errors or symbol is None or amount is None:
        return None, errors
    try:
        normalized_eid, normalized_pair = validate_fleet_request(eid, symbol)
    except FleetPreflightError as exc:
        return None, [str(exc)]
    return FleetBacktestRequest(normalized_eid, normalized_pair, amount), []


def format_eta(seconds: int | None) -> str:
    if seconds is None or seconds < 0:
        return ""
    if seconds < 60:
        return f"{seconds}s"
    minutes, secs = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}m {secs}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes}m"


def progress_line(snapshot: dict[str, Any] | None) -> str:
    """One status line from a fleet runner snapshot or progress-file copy."""
    if not snapshot:
        return ""
    parts: list[str] = []
    phase = str(snapshot.get("phase") or "")
    if phase and phase != "complete":
        parts.append(phase.replace("_", " "))
    total = int(snapshot.get("total_combinations") or snapshot.get("total") or 0)
    done = int(snapshot.get("completed") or 0)
    if total > 0:
        pct = int(snapshot.get("progress_pct") or (done * 100 // total))
        parts.append(f"{done}/{total} ({pct}%)")
    current = str(snapshot.get("current_test") or "").strip()
    if current:
        parts.append(current)
    if snapshot.get("status") == "running":
        eta = format_eta(snapshot.get("eta_seconds"))
        if eta:
            parts.append(f"ETA {eta}")
    msgs = snapshot.get("messages")
    if isinstance(msgs, list) and msgs:
        parts.append(str(msgs[-1]))
    return " · ".join(parts)


def timeframe_label(tv_interval: str) -> str:
    return TRADINGVIEW_INTERVAL_LABELS.get(tv_interval, tv_interval)


def plan_timeframe_from_row(tv_interval: str) -> str | None:
    """Map a fleet TV interval to a device plan timeframe, when supported."""
    mapping = {"60": "1h", "240": "4h"}
    plan_tf = mapping.get(tv_interval.strip())
    return plan_tf if plan_tf in TIMEFRAMES else None


def plan_prefill_from_row(
    row: dict[str, Any],
    *,
    pair: str,
    stake_usd: float,
) -> tuple[dict[str, str] | None, str]:
    """Fields for Plan builder, or None with a note when the row cannot map cleanly."""
    indicator = str(row.get("strategy_id") or "")
    if indicator not in LIVE_V1_INDICATORS:
        return None, f"Indicator {indicator!r} is not on the live plan list yet."
    plan_tf = plan_timeframe_from_row(str(row.get("timeframe") or ""))
    if plan_tf is None:
        tv = str(row.get("timeframe") or "")
        return None, (
            f"Timeframe {timeframe_label(tv)} is not on the device plan list "
            f"({' or '.join(TIMEFRAMES)})."
        )
    from trendalgo.device.fields import TRAILING_STOP_MIN

    tsl = row.get("trailing_stop_pct")
    if isinstance(tsl, (int, float)) and tsl > 0:
        stop = f"{float(tsl) * 100:g}"
    else:
        # Last resort when a fleet row still lacks a trail (Results should stamp one).
        stop = f"{int(TRAILING_STOP_MIN)}"
    rank = row.get("rank", "?")
    name = f"Fleet #{rank} {indicator}"[:40]
    return {
        "name": name,
        "pair": pair,
        "timeframe": plan_tf,
        "indicator": indicator,
        "stake": f"{stake_usd:g}",
        "stop": stop,
    }, ""


def top10_table_rows(
    top10: list[dict[str, Any]],
    buy_hold: dict[str, Any] | None,
) -> list[tuple[str, ...]]:
    bh_net = (
        float(buy_hold["net_profit"])
        if buy_hold and buy_hold.get("net_profit") is not None
        else None
    )
    rows: list[tuple[str, ...]] = []
    for row in top10:
        net = float(row.get("net_profit") or 0.0)
        vs = ""
        if bh_net is not None:
            vs = f"{net - bh_net:+.2f}"
        rows.append(
            (
                str(row.get("rank", "")),
                str(row.get("strategy_id", "")),
                timeframe_label(str(row.get("timeframe", ""))),
                f"${net:,.2f}",
                str(int(row.get("trades") or 0)),
                vs if vs else "—",
            )
        )
    return rows
