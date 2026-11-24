"""AV-G-DSH3 — Settings dashboard module min editors."""

from __future__ import annotations

from pathlib import Path

from trendalgo.device.portfolio_layout_prefs import load_prefs
from trendalgo.results_store.desk_dashboard import (
    apply_dashboard_module_mins,
    load_dashboard_surface,
)


def test_dashboard_module_mins_roundtrip(tmp_path: Path) -> None:
    data = load_dashboard_surface(tmp_path)
    assert data["module_mins"]
    row = next(r for r in data["module_mins"] if r["id"] == "total_worth")
    new_w = min(row["max_w"], row["default_w"] + 1)
    new_h = min(row["max_h"], row["default_h"] + 1)
    result = apply_dashboard_module_mins(
        tmp_path,
        {"mins": [{"id": "total_worth", "min_w": new_w, "min_h": new_h}]},
    )
    assert result["ok"] is True
    assert result["count"] >= 1
    prefs = load_prefs(tmp_path)
    assert prefs.module_mins["total_worth"] == (new_w, new_h)
    reset = apply_dashboard_module_mins(tmp_path, {"reset": True})
    assert reset["ok"] is True
    assert load_prefs(tmp_path).module_mins == {}
