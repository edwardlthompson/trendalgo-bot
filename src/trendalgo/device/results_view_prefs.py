"""Shared Backtest / Scanner Results view prefs (heatmap, Perfect Strategies)."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from trendalgo.device.profile import read_json, write_json

PREFS_FILE = "results_view_prefs.json"


_DEFAULT_DIALOG_W = 720
_DEFAULT_DIALOG_H = 480
_MIN_DIALOG_W = 520
_MIN_DIALOG_H = 360


@dataclass
class ResultsViewPrefs:
    heatmap_enabled: bool = False
    perfect_only: bool = False
    last_pair: str = "BTC/USD"
    results_dialog_width: int = _DEFAULT_DIALOG_W
    results_dialog_height: int = _DEFAULT_DIALOG_H
    results_dialog_maximized: bool = False


def prefs_path(root: Path) -> Path:
    return root / PREFS_FILE


def load_results_prefs(root: Path) -> ResultsViewPrefs:
    raw = read_json(prefs_path(root))
    if not isinstance(raw, dict):
        return ResultsViewPrefs()
    return ResultsViewPrefs(
        heatmap_enabled=_bool(raw.get("heatmap_enabled"), False),
        perfect_only=_bool(raw.get("perfect_only"), False),
        last_pair=str(raw.get("last_pair") or "BTC/USD").strip().upper() or "BTC/USD",
        results_dialog_width=_size(
            raw.get("results_dialog_width"), _DEFAULT_DIALOG_W, _MIN_DIALOG_W
        ),
        results_dialog_height=_size(
            raw.get("results_dialog_height"), _DEFAULT_DIALOG_H, _MIN_DIALOG_H
        ),
        results_dialog_maximized=_bool(raw.get("results_dialog_maximized"), False),
    )


def save_results_prefs(root: Path, prefs: ResultsViewPrefs) -> None:
    write_json(prefs_path(root), asdict(prefs))


def _bool(raw: Any, default: bool) -> bool:
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, str):
        return raw.strip().lower() in {"1", "true", "yes", "on"}
    return default


def _size(raw: Any, default: int, minimum: int) -> int:
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return default
    return max(minimum, value)
