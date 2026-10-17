"""Opt-in flag: save crash details locally for the operator to review."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from trendalgo.device.profile import read_json, write_json

PREFS_FILE = "crash_prefs.json"


def prefs_path(root: Path) -> Path:
    return root / PREFS_FILE


def get_save_crashes(root: Path) -> bool:
    raw = read_json(prefs_path(root))
    if not isinstance(raw, dict):
        return False
    return _bool(raw.get("save_crashes"), False)


def set_save_crashes(root: Path, on: bool) -> None:
    write_json(prefs_path(root), {"save_crashes": bool(on)})


def _bool(raw: Any, default: bool) -> bool:
    if isinstance(raw, bool):
        return raw
    return default
