"""Headless rich Telegram + alert-history emitter for Avalonia desk scans."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from trendalgo.device.lts_scan_model import (
    filter_coins,
    load_filters,
    load_lts_rows,
    load_watchlist,
)
from trendalgo.device.scan_alerts import process_scan_alerts
from trendalgo.device.scanner_alert_diff import AlertEvent
from trendalgo.device.scanner_alerts_store import append_log_alert
from trendalgo.notifications.telegram import TelegramCommands

_FLOOR_KEYS = (
    "min_gain_7d",
    "min_gain_30d",
    "min_gain_pct",
    "min_best_bt",
    "chart_dist_max_7d",
    "chart_dist_max_30d",
    "health_min",
    "vol24_min",
)


def _opt_float(raw: object) -> float | None:
    if raw in (None, "", "-", "All"):
        return None
    try:
        return float(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _alert_floors(filters: dict[str, Any]) -> dict[str, float]:
    out: dict[str, float] = {}
    for key in _FLOOR_KEYS:
        val = _opt_float(filters.get(key))
        if val is not None:
            out[key] = val
    vol_floor = _opt_float(filters.get("min_volume_usd"))
    if vol_floor is not None and vol_floor > 0:
        out["min_volume_usd"] = vol_floor
    if bool(filters.get("require_continuous_1h", True)):
        out["require_continuous_1h"] = 1.0
    return out


def _filtered_coins(
    board_coins: list[dict[str, Any]], filters: dict[str, Any]
) -> list[dict[str, Any]]:
    raw_ex = filters.get("view_exchanges")
    exchanges = (
        [str(x).strip().lower() for x in raw_ex if str(x).strip()]
        if isinstance(raw_ex, list) and raw_ex
        else None
    )
    return filter_coins(
        board_coins,
        exchanges=exchanges,
        min_gain_7d=_opt_float(filters.get("min_gain_7d")),
        min_gain_30d=_opt_float(
            filters.get("min_gain_30d")
            if "min_gain_30d" in filters
            else filters.get("min_gain_pct")
        ),
        min_best_bt=_opt_float(filters.get("min_best_bt")),
        bot_vs_bh_filter=str(filters.get("bot_vs_bh_filter") or "") or None,
        chart_dist_max_7d=_opt_float(filters.get("chart_dist_max_7d")),
        chart_dist_max_30d=_opt_float(filters.get("chart_dist_max_30d")),
        health_min=_opt_float(filters.get("health_min")),
        vol_accel_filter=str(filters.get("vol_accel_filter") or "") or None,
        vol24_min=_opt_float(filters.get("vol24_min")),
    )


def emit_desk_scan_alerts(
    root: Path,
    *,
    lane: str = "crypto",
    telegram: TelegramCommands | None = None,
) -> list[AlertEvent]:
    """Diff Qualified enters/leaves for a lane, persist alerts, and dispatch rich Telegram cards."""
    key = str(lane or "crypto").strip().lower() or "crypto"
    board_coins = [r for r in load_lts_rows(root, lane=key) if isinstance(r, dict)]
    filters = load_filters(root, lane=key)
    alertable = _filtered_coins(board_coins, filters)
    watch = load_watchlist(root, lane=key)
    events, _history = process_scan_alerts(
        root,
        coins=alertable,
        watchlist_pairs=watch,
        telegram=telegram,
        floors=_alert_floors(filters),
        board_coins=board_coins,
        lane=key,
    )
    append_log_alert(
        root,
        kind="scan_log",
        reason=(
            f"{key} scan finished: {len(board_coins)} qualified · "
            f"{len(alertable)} after filters · {len(events)} alert(s)"
        ),
    )
    return events
