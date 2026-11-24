"""Settings → 10-section layout grid + ribbon prefs (AV-G-SET5)."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from trendalgo.device import strings as S
from trendalgo.device.portfolio_layout_prefs import Placement
from trendalgo.device.settings_layout_prefs import (
    SECTION_IDS,
    SECTION_MINS,
    SECTION_TITLES,
    SettingsLayoutPrefs,
    factory_defaults,
    load_settings_layout,
    save_settings_layout,
)

__all__ = ["apply_settings_layout", "load_settings_layout_surface"]


def load_settings_layout_surface(root: Path) -> dict[str, Any]:
    prefs = load_settings_layout(root)
    ordered = sorted(prefs.placements, key=lambda p: (p.row, p.col, p.id))
    return {
        "ok": True,
        "edit_mode": bool(prefs.edit_mode),
        "layout_version": int(prefs.layout_version),
        "grid": asdict(prefs.grid),
        "help": S.SETTINGS_LAYOUT_EDIT_TIP,
        "no_secret": S.SETTINGS_NO_SECRET,
        "ribbon": {
            "save": S.SETTINGS_SAVE,
            "wizard": S.SETTINGS_WIZARD,
            "telegram": S.NOTIFY_TELEGRAM_WIZARD,
            "alpaca": S.NOTIFY_ALPACA_WIZARD,
            "arrange": S.SETTINGS_LAYOUT_EDIT,
        },
        "section_ids": list(SECTION_IDS),
        "sections": [
            {
                "id": p.id,
                "title": SECTION_TITLES.get(p.id, p.id),
                "col": int(p.col),
                "row": int(p.row),
                "w": int(p.w),
                "h": int(p.h),
                "min_w": SECTION_MINS[p.id][0],
                "min_h": SECTION_MINS[p.id][1],
            }
            for p in ordered
            if p.id in SECTION_IDS
        ],
    }


def apply_settings_layout(root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    edit_mode = bool(payload.get("edit_mode", True))
    if payload.get("reset"):
        prefs = factory_defaults()
        prefs.edit_mode = edit_mode
        save_settings_layout(root, prefs)
        out = load_settings_layout_surface(root)
        out["ok"] = True
        return out

    current = load_settings_layout(root)
    placements: list[Placement] = []
    raw_sections = payload.get("sections")
    if isinstance(raw_sections, list):
        for item in raw_sections:
            if not isinstance(item, dict):
                continue
            sid = str(item.get("id") or "").strip()
            if sid not in SECTION_IDS:
                continue
            mw, mh = SECTION_MINS[sid]
            placements.append(
                Placement(
                    id=sid,
                    col=max(0, int(item.get("col") or 0)),
                    row=max(0, int(item.get("row") or 0)),
                    w=max(mw, int(item.get("w") or 24)),
                    h=max(mh, int(item.get("h") or mh)),
                )
            )
    if not placements:
        return {"ok": False, "error": "no_sections"}

    known = {p.id for p in placements}
    defaults = {p.id: p for p in factory_defaults().placements}
    for sid in SECTION_IDS:
        if sid not in known:
            placements.append(defaults[sid])

    prefs = SettingsLayoutPrefs(
        grid=current.grid,
        placements=placements,
        layout_version=current.layout_version,
        edit_mode=edit_mode,
    )
    if isinstance(payload.get("grid"), dict):
        g = payload["grid"]
        prefs.grid.cols = int(g.get("cols") or prefs.grid.cols)
        prefs.grid.rows = int(g.get("rows") or prefs.grid.rows)
        prefs.grid.show_grid = bool(g.get("show_grid", prefs.grid.show_grid))
    save_settings_layout(root, prefs)
    out = load_settings_layout_surface(root)
    out["ok"] = True
    return out
