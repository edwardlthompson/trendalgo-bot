"""Persist last qualified set and alert history for the device Alerts tab."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from trendalgo.device.profile import read_json, write_json
from trendalgo.device.scanner_alert_diff import AlertEvent

STATE_FILE = "scanner_alert_state.json"
HISTORY_FILE = "scanner_alerts.json"
MAX_HISTORY = 100


def load_previous_qualified(root: Path) -> set[str]:
    raw = read_json(root / STATE_FILE)
    if not isinstance(raw, dict):
        return set()
    keys = raw.get("qualified")
    if not isinstance(keys, list):
        return set()
    return {str(k).upper() for k in keys if str(k).strip()}


def save_previous_qualified(root: Path, keys: set[str]) -> None:
    write_json(
        root / STATE_FILE,
        {
            "qualified": sorted(keys),
            "updated_at": datetime.now(tz=UTC).isoformat(),
        },
    )


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


def load_history(root: Path) -> list[dict[str, Any]]:
    raw = read_json(root / HISTORY_FILE)
    if not isinstance(raw, dict):
        return []
    rows = raw.get("alerts")
    if not isinstance(rows, list):
        return []
    return [r for r in rows if isinstance(r, dict)]
