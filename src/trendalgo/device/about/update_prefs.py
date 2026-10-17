"""Device-local update/donate prefs (profile JSON; not peer-synced)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from trendalgo.device.profile import read_json, write_json

PREFS_FILE = "update_prefs.json"


@dataclass
class UpdatePrefs:
    last_check_at: float | None = None
    last_seen_version: str | None = None
    dismissed_version: str | None = None


def prefs_path(root: Path) -> Path:
    return root / PREFS_FILE


def load_update_prefs(root: Path) -> UpdatePrefs:
    raw = read_json(prefs_path(root))
    if not isinstance(raw, dict):
        return UpdatePrefs()
    return UpdatePrefs(
        last_check_at=_num(raw.get("last_check_at")),
        last_seen_version=_str(raw.get("last_seen_version")),
        dismissed_version=_str(raw.get("dismissed_version")),
    )


def mark_update_checked(root: Path, now: float, dismissed_version: str | None = None) -> None:
    prefs = load_update_prefs(root)
    prefs.last_check_at = now
    if dismissed_version:
        prefs.dismissed_version = dismissed_version
    _save(root, prefs)


def mark_version_seen(root: Path, version: str) -> None:
    prefs = load_update_prefs(root)
    prefs.last_seen_version = version
    _save(root, prefs)


def _save(root: Path, prefs: UpdatePrefs) -> None:
    doc: dict[str, Any] = {
        "last_check_at": prefs.last_check_at,
        "last_seen_version": prefs.last_seen_version,
        "dismissed_version": prefs.dismissed_version,
    }
    write_json(prefs_path(root), doc)


def _num(raw: Any) -> float | None:
    if isinstance(raw, (int, float)):
        return float(raw)
    return None


def _str(raw: Any) -> str | None:
    return raw if isinstance(raw, str) and raw else None
