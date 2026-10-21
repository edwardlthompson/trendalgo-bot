"""Settings tab module grid layout (profile JSON)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from trendalgo.device.portfolio_layout_prefs import GridPrefs, Placement
from trendalgo.device.profile import ProfileError, read_json, write_json

PREFS_FILE = "settings_layout_prefs.json"
# v3: 48-col square grid; Save/wizards moved to Settings ribbon (no actions module).
_LAYOUT_VERSION = 3

# Stable section ids → default 2-column placements (48-col square grid).
SECTION_IDS: tuple[str, ...] = (
    "connection",
    "appearance",
    "keys",
    "venue",
    "dashboard",
    "privacy",
    "data",
    "notify",
    "about",
)

SECTION_TITLES: dict[str, str] = {
    "connection": "Connection",
    "appearance": "Appearance",
    "keys": "Exchange API keys",
    "venue": "Venue",
    "dashboard": "Dashboard modules",
    "privacy": "Privacy",
    "data": "Data",
    "notify": "Notifications",
    "about": "About",
}

# Grid-cell mins (cols, rows) on 48-col squares — keep forms readable when shrunk.
SECTION_MINS: dict[str, tuple[int, int]] = {
    "connection": (12, 8),
    "appearance": (12, 8),
    "keys": (12, 12),
    "venue": (12, 8),
    "dashboard": (12, 8),
    "privacy": (12, 4),
    "data": (8, 4),
    "notify": (12, 10),
    "about": (12, 10),
}


def _settings_grid() -> GridPrefs:
    return GridPrefs(cols=48, rows=96, gap_px=6, row_px=0.0)


@dataclass
class SettingsLayoutPrefs:
    grid: GridPrefs = field(default_factory=_settings_grid)
    placements: list[Placement] = field(default_factory=list)
    layout_version: int = _LAYOUT_VERSION
    edit_mode: bool = True


def prefs_path(root: Path) -> Path:
    return root / PREFS_FILE


def factory_defaults() -> SettingsLayoutPrefs:
    # Two columns of 24 grid units; stack by section order (heights refined by fit).
    left = ("connection", "appearance", "keys", "venue")
    right = ("dashboard", "privacy", "data", "notify", "about")
    placements: list[Placement] = []
    row = 0
    for sid in left:
        _mw, mh = SECTION_MINS[sid]
        placements.append(Placement(id=sid, col=0, row=row, w=24, h=mh))
        row += mh
    row = 0
    for sid in right:
        _mw, mh = SECTION_MINS[sid]
        placements.append(Placement(id=sid, col=24, row=row, w=24, h=mh))
        row += mh
    return SettingsLayoutPrefs(placements=placements)


def load_settings_layout(root: Path) -> SettingsLayoutPrefs:
    try:
        raw = read_json(prefs_path(root))
    except ProfileError:
        return factory_defaults()
    if not isinstance(raw, dict):
        return factory_defaults()
    try:
        version = int(raw.get("layout_version") or 0)
    except (TypeError, ValueError):
        version = 0
    if version < _LAYOUT_VERSION:
        return factory_defaults()
    try:
        return _parse(raw)
    except (TypeError, ValueError, KeyError):
        return factory_defaults()


def save_settings_layout(root: Path, prefs: SettingsLayoutPrefs) -> None:
    write_json(prefs_path(root), asdict(prefs))


def _parse(raw: dict[str, Any]) -> SettingsLayoutPrefs:
    grid_raw = raw.get("grid") if isinstance(raw.get("grid"), dict) else {}
    try:
        row_px = float(grid_raw.get("row_px") or 0.0)
    except (TypeError, ValueError):
        row_px = 0.0
    grid = GridPrefs(
        cols=int(grid_raw.get("cols") or 48),
        rows=int(grid_raw.get("rows") or 96),
        gap_px=int(grid_raw.get("gap_px") or 6),
        magnet_px=int(grid_raw.get("magnet_px") or 16),
        show_grid=bool(grid_raw.get("show_grid")),
        row_px=max(0.0, row_px),
    )
    placements: list[Placement] = []
    for item in raw.get("placements") or []:
        if not isinstance(item, dict):
            continue
        sid = str(item.get("id") or "").strip()
        if sid not in SECTION_IDS:
            continue
        placements.append(
            Placement(
                id=sid,
                col=int(item.get("col") or 0),
                row=int(item.get("row") or 0),
                w=max(4, int(item.get("w") or 24)),
                h=max(2, int(item.get("h") or 4)),
            )
        )
    if not placements:
        return factory_defaults()
    known = {p.id for p in placements}
    defaults = {p.id: p for p in factory_defaults().placements}
    for sid in SECTION_IDS:
        if sid not in known:
            placements.append(defaults[sid])
    return SettingsLayoutPrefs(
        grid=grid,
        placements=placements,
        layout_version=_LAYOUT_VERSION,
        edit_mode=bool(raw.get("edit_mode", True)),
    )
