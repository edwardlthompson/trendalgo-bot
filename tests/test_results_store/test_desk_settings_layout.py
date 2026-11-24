"""AV-G-SET5 — settings 10-section layout surface + apply."""

from __future__ import annotations

from pathlib import Path

from trendalgo.device.settings_layout_prefs import SECTION_IDS, load_settings_layout
from trendalgo.results_store.desk_settings_layout import (
    apply_settings_layout,
    load_settings_layout_surface,
)


def test_settings_layout_surface_has_ten_sections(tmp_path: Path) -> None:
    data = load_settings_layout_surface(tmp_path)
    assert data["ok"] is True
    assert len(data["sections"]) == 10
    assert {s["id"] for s in data["sections"]} == set(SECTION_IDS)
    assert data["ribbon"]["arrange"]
    assert data["help"]


def test_apply_settings_layout_reorder(tmp_path: Path) -> None:
    base = load_settings_layout_surface(tmp_path)
    sections = list(reversed(base["sections"]))
    for i, s in enumerate(sections):
        s["row"] = i * 8
        s["col"] = 0 if i < 5 else 24
    result = apply_settings_layout(
        tmp_path,
        {"edit_mode": True, "sections": sections},
    )
    assert result["ok"] is True
    prefs = load_settings_layout(tmp_path)
    assert prefs.edit_mode is True
    assert len(prefs.placements) == 10
    ids = [p.id for p in sorted(prefs.placements, key=lambda p: (p.row, p.col, p.id))]
    assert ids[0] == sections[0]["id"]


def test_apply_settings_layout_reset(tmp_path: Path) -> None:
    apply_settings_layout(
        tmp_path,
        {
            "edit_mode": False,
            "sections": [
                {"id": "about", "col": 0, "row": 0, "w": 24, "h": 10},
            ],
        },
    )
    result = apply_settings_layout(tmp_path, {"reset": True, "edit_mode": True})
    assert result["ok"] is True
    assert result["edit_mode"] is True
    assert len(result["sections"]) == 10
