"""Persist last qualified set/coins and alert history for the device Alerts tab."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from trendalgo.device.profile import read_json, write_json
from trendalgo.device.scanner_alert_diff import AlertEvent, coins_by_key

STATE_FILE = "scanner_alert_state.json"
HISTORY_FILE = "scanner_alerts.json"
MAX_HISTORY = 200


def load_previous_qualified(root: Path) -> set[str]:
    raw = read_json(root / STATE_FILE)
    if not isinstance(raw, dict):
        return set()
    keys = raw.get("qualified")
    if not isinstance(keys, list):
        return set()
    return {str(k).upper() for k in keys if str(k).strip()}


def load_previous_coins(root: Path) -> dict[str, dict[str, Any]]:
    raw = read_json(root / STATE_FILE)
    if not isinstance(raw, dict):
        return {}
    coins = raw.get("coins")
    if not isinstance(coins, dict):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for key, coin in coins.items():
        if isinstance(coin, dict):
            out[str(key).upper()] = coin
    return out


def save_previous_qualified(
    root: Path,
    keys: set[str],
    *,
    coins: list[dict[str, Any]] | None = None,
) -> None:
    payload: dict[str, Any] = {
        "qualified": sorted(keys),
        "updated_at": datetime.now(tz=UTC).isoformat(),
    }
    if coins is not None:
        by_key = coins_by_key(coins)
        # Keep a slim snapshot for leave-reason diffs.
        slim: dict[str, dict[str, Any]] = {}
        for key, coin in by_key.items():
            slim[key] = {
                k: coin.get(k)
                for k in (
                    "symbol",
                    "pair",
                    "volume_24h",
                    "volume_usd",
                    "uniformity_score",
                    "uniformity",
                    "gain_30d",
                    "gain_pct",
                    "gain_7d",
                    "health",
                )
                if k in coin
            }
        payload["coins"] = slim
    write_json(root / STATE_FILE, payload)


def append_alerts(root: Path, events: list[AlertEvent]) -> list[dict[str, Any]]:
    if not events:
        return load_history(root)
    history = load_history(root)
    now = datetime.now(tz=UTC).isoformat()
    for event in events:
        history.insert(
            0,
            {
                "kind": event.kind,
                "symbol": event.symbol,
                "pair": event.pair,
                "reason": event.reason,
                "at": now,
            },
        )
    history = history[:MAX_HISTORY]
    write_json(root / HISTORY_FILE, {"alerts": history})
    return history


def append_log_alert(
    root: Path,
    *,
    kind: str,
    reason: str,
    symbol: str = "",
    pair: str = "",
) -> list[dict[str, Any]]:
    return append_alerts(
        root,
        [AlertEvent(kind=kind, symbol=symbol, pair=pair or symbol, reason=reason)],
    )


def load_history(root: Path) -> list[dict[str, Any]]:
    raw = read_json(root / HISTORY_FILE)
    if not isinstance(raw, dict):
        return []
    rows = raw.get("alerts")
    if not isinstance(rows, list):
        return []
    return [r for r in rows if isinstance(r, dict)]


def history_for_tab(rows: list[dict[str, Any]], tab: str) -> list[dict[str, Any]]:
    kinds = {
        "logs": {"scan_log", "backtest_log"},
        "entered": {"qualified_enter"},
        "left": {"watchlist_leave"},
        "trades": {"trade_alert"},
    }.get(tab, set())
    if not kinds:
        return list(rows)
    return [r for r in rows if str(r.get("kind") or "") in kinds]
