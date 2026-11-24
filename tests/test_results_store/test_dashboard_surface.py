"""Dashboard module catalog + live canvas tiles (AV-G-DSH1)."""

from __future__ import annotations

from pathlib import Path

from trendalgo.results_store.desk_export import load_dashboard_surface


def test_dashboard_surface_lists_wired_modules(tmp_path: Path) -> None:
    data = load_dashboard_surface(tmp_path)
    ids = {m["id"] for m in data["modules"]}
    assert "total_worth" in ids
    assert "events_calendar" in ids
    assert data["count"] >= 10
    assert data["ranges"] == ["1D", "1W", "1M", "3M", "YTD", "1Y"]
    assert data["pages"]
    assert data["tiles"]
    assert data["tile_count"] == len(data["tiles"])
    assert data["grid"]["cols"] >= 4
    tile = data["tiles"][0]
    for key in ("id", "title", "col", "row", "w", "h", "value", "detail"):
        assert key in tile
    assert data["demo"] is False
    (tmp_path / "portfolio-demo.db").write_bytes(b"")
    assert load_dashboard_surface(tmp_path)["demo"] is True
