"""AV-G-DSH1 — dashboard surface exposes canvas tiles for Avalonia."""

from __future__ import annotations

from pathlib import Path

from trendalgo.results_store.desk_dashboard import load_dashboard_surface


def test_dashboard_canvas_tile_geometry(tmp_path: Path) -> None:
    data = load_dashboard_surface(tmp_path)
    assert data["tile_count"] >= 1
    assert all(t["w"] > 0 and t["h"] > 0 for t in data["tiles"])
    assert data["active_page_id"]
