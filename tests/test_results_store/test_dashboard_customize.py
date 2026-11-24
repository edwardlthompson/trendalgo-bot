"""AV-G-DSH2 — dashboard customize pack + persist."""

from __future__ import annotations

from pathlib import Path

from trendalgo.device.portfolio_layout_prefs import load_prefs
from trendalgo.results_store.desk_dashboard import apply_dashboard_customize, load_dashboard_surface


def test_apply_dashboard_customize_packs(tmp_path: Path) -> None:
    before = load_dashboard_surface(tmp_path)
    assert before["customize"]
    result = apply_dashboard_customize(
        tmp_path,
        {"module_ids": ["total_worth", "assets"], "cols": 24, "rows": 20, "show_grid": True},
    )
    assert result["ok"] is True
    assert result["count"] == 2
    assert result["show_grid"] is True
    prefs = load_prefs(tmp_path)
    page = next(p for p in prefs.pages if p.id == prefs.active_page_id)
    assert {p.id for p in page.placements} == {"total_worth", "assets"}
    after = load_dashboard_surface(tmp_path)
    assert after["tile_count"] == 2
    checked = {m["id"] for g in after["customize"] for m in g["modules"] if m["checked"]}
    assert checked == {"total_worth", "assets"}
