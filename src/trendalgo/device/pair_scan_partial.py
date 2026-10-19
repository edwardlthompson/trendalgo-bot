"""Live partial All-TA results (worker writes; Backtest page polls + ranks)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from trendalgo.device.backtest_sort import DEFAULT_SORT_DIR, DEFAULT_SORT_KEY, sort_rows
from trendalgo.device.profile import ProfileError, read_json, write_json

PARTIAL_FILE = "pair_strategy_scan_partial.json"


def partial_path(root: Path) -> Path:
    return root / PARTIAL_FILE


def write_partial_rows(root: Path, rows: list[dict[str, Any]]) -> None:
    """Atomically publish ranked snapshot for the UI poller."""
    ranked = sort_rows(list(rows), key=DEFAULT_SORT_KEY, direction=DEFAULT_SORT_DIR)
    try:
        write_json(partial_path(root), {"rows": ranked, "count": len(ranked)})
    except OSError:
        pass


def read_partial_rows(root: Path) -> list[dict[str, Any]] | None:
    try:
        raw = read_json(partial_path(root))
    except ProfileError:
        return None
    if not isinstance(raw, dict):
        return None
    rows = raw.get("rows")
    return rows if isinstance(rows, list) else None


def clear_partial_rows(root: Path) -> None:
    partial_path(root).unlink(missing_ok=True)
