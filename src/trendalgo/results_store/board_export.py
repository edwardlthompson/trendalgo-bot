"""Export LTS lane board rows for Avalonia DataGrid (AV-G2)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from trendalgo.device.lts_scan_model import load_lts_rows
from trendalgo.device.profile import read_json
from trendalgo.device.scan_identity import row_key

BOARD_TABS = ("qualified", "watchlist", "logs")


def _watch_keys(root: Path, lane: str) -> set[str]:
    path = root / (
        "scanner_watchlist.json" if lane in {"", "crypto"} else f"scanner_watchlist_{lane}.json"
    )
    data = read_json(path)
    if not isinstance(data, dict):
        return set()
    raw = data.get("pairs") or data.get("keys") or data.get("watch") or []
    if not isinstance(raw, list):
        return set()
    return {str(x).strip().upper() for x in raw if str(x).strip()}


def _normalize(row: dict[str, Any], *, watched: bool) -> dict[str, Any]:
    pair = str(row.get("pair") or "").strip()
    bot_raw = row.get("bot_vs_bh_pct")
    try:
        bot_vs = float(bot_raw) if bot_raw is not None else None
    except (TypeError, ValueError):
        bot_vs = None
    return {
        "pair": pair,
        "symbol": str(row.get("symbol") or pair.split("/")[0] if pair else ""),
        "exchange": str(row.get("exchange") or row.get("exchange_id") or ""),
        "gain": float(row.get("gain") or row.get("gain_pct") or 0.0),
        "volume_score": float(row.get("volume_score") or row.get("vol_score") or 0.0),
        "watch": bool(row.get("watch")) or watched,
        "health": str(row.get("health") or row.get("grade") or ""),
        "bot_vs_bh_pct": bot_vs,
        "ohlcv_source": str(row.get("ohlcv_source") or row.get("bar_source") or ""),
        "payload": row,
    }


def load_lane_board(
    root: Path,
    *,
    lane: str = "crypto",
    tab: str = "qualified",
) -> list[dict[str, Any]]:
    tab_key = str(tab or "qualified").strip().lower()
    if tab_key not in BOARD_TABS:
        raise ValueError(f"unknown board tab: {tab}")
    if tab_key == "logs":
        return []
    lane_key = str(lane or "crypto").strip().lower() or "crypto"
    raw = load_lts_rows(root, lane=lane_key)
    watch_ids = _watch_keys(root, lane_key)
    out: list[dict[str, Any]] = []
    for row in raw:
        if not isinstance(row, dict):
            continue
        key = row_key(row) or str(row.get("pair") or "").upper()
        watched = (
            bool(row.get("watch"))
            or key.upper() in watch_ids
            or str(row.get("pair") or "").upper() in watch_ids
        )
        if tab_key == "watchlist" and not watched:
            continue
        out.append(_normalize(row, watched=watched))
    return out
