"""Persist lightweight UI chrome state (last nav page) under the device profile."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from trendalgo.device.nav_layout import (
    LEGACY_INT_TO_GLYPH,
    NAV_BY_GLYPH,
    NAV_GLYPH_BY_INDEX,
    PORTFOLIO,
)
from trendalgo.device.profile import read_json, write_json

UI_STATE_FILE = "ui_state.json"


def ui_state_path(root: Path) -> Path:
    return root / UI_STATE_FILE


def load_nav_page(root: Path) -> int | None:
    """Last nav page index, or None when the user has never left a tab (first open)."""
    raw = read_json(ui_state_path(root))
    if not isinstance(raw, dict):
        return None
    return _parse_page(raw.get("nav_page"))


def save_nav_page(root: Path, index: int) -> None:
    """Remember the active tab for the next launch (stable glyph id)."""
    glyph = NAV_GLYPH_BY_INDEX.get(index)
    if glyph is None:
        return
    previous = read_json(ui_state_path(root)) or {}
    if not isinstance(previous, dict):
        previous = {}
    previous["nav_page"] = glyph
    write_json(ui_state_path(root), previous)


def default_nav_page(root: Path) -> int:
    """Portfolio on first open; otherwise the last tab the user left."""
    saved = load_nav_page(root)
    return PORTFOLIO if saved is None else saved


def _parse_page(raw: Any) -> int | None:
    if isinstance(raw, str):
        return NAV_BY_GLYPH.get(raw.strip().lower())
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    # Integers are the pre-Alerts catalog order.
    glyph = LEGACY_INT_TO_GLYPH.get(value)
    return NAV_BY_GLYPH.get(glyph) if glyph else None
