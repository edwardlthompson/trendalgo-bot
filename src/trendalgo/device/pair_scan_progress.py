"""Pair strategy-scan progress file (worker writes; Backtest page polls)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from trendalgo.device.profile import ProfileError, read_json, write_json

PROGRESS_FILE = "pair_strategy_scan_progress.json"


def progress_path(root: Path) -> Path:
    return root / PROGRESS_FILE


def write_progress(root: Path, payload: dict[str, Any]) -> None:
    try:
        out = dict(payload)
        existing = read_progress(root)
        events: list[str] = []
        if isinstance(existing, dict) and isinstance(existing.get("events"), list):
            events = [str(x) for x in existing["events"] if str(x).strip()]
        msg = str(out.get("message") or "").strip()
        if msg and (not events or events[-1] != msg):
            events.append(msg)
        if len(events) > 120:
            events = events[-120:]
        out["events"] = events
        write_json(progress_path(root), out)
    except OSError:
        pass


def read_progress(root: Path) -> dict[str, Any] | None:
    try:
        raw = read_json(progress_path(root))
    except ProfileError:
        return None
    return raw if isinstance(raw, dict) else None


def clear_progress(root: Path) -> None:
    progress_path(root).unlink(missing_ok=True)


def progress_line(raw: dict[str, Any] | None) -> str:
    if not raw:
        return ""
    message = str(raw.get("message") or "").strip()
    if message:
        return message
    return str(raw.get("line") or "").strip()
