"""Dashboard layout prefs + grid snap unit tests."""

from __future__ import annotations

from pathlib import Path

from pytestqt.qtbot import QtBot

from trendalgo.device.portfolio_grid_snap import (
    Rect,
    cell_size,
    find_free_or_swap,
    overlaps,
    push_aside_for_resize,
    resize_allowed,
    snap_point,
    snap_resize,
)
from trendalgo.device.portfolio_layout_prefs import (
    Placement,
    factory_defaults,
    load_prefs,
    save_prefs,
)
from trendalgo.device.portfolio_module_catalog import effective_spec, spec_for


def test_factory_defaults_three_pages_24_col() -> None:
    prefs = factory_defaults()
    assert len(prefs.pages) == 3
    assert prefs.pages[0].id == "overview"
    assert prefs.grid.cols == 24
    assert prefs.layout_version == 3
    assert any(p.id == "total_worth" for p in prefs.pages[0].placements)
    tw = next(p for p in prefs.pages[0].placements if p.id == "total_worth")
    assert tw.h >= 5
    heat = next(p for p in prefs.pages[1].placements if p.id == "heatmap")
    assert heat.h >= 8


def test_cell_size_is_square() -> None:
    cw, ch = cell_size(1200, 800, 24, 24, 8)
    assert cw == ch
    assert cw > 1.0


def test_cell_size_fixed_row_pitch() -> None:
    cw, ch = cell_size(1200, 800, 24, 24, 8, fixed_row_px=32.0)
    assert cw > 1.0
    assert ch == 32.0
    assert cw != ch


def test_prefs_round_trip(tmp_path: Path) -> None:
    prefs = factory_defaults()
    prefs.grid.cols = 20
    prefs.range = "7d"
    save_prefs(tmp_path, prefs)
    loaded = load_prefs(tmp_path)
    assert loaded.grid.cols == 20
    assert loaded.range == "7d"
    assert loaded.pages[0].placements[0].id == "total_worth"


def test_prefs_round_trip_resized_spans(tmp_path: Path) -> None:
    prefs = factory_defaults()
    page = prefs.pages[0]
    page.placements = [
        Placement(id="total_worth", col=0, row=0, w=16, h=5),
        Placement(id="assets", col=0, row=5, w=12, h=8),
    ]
    save_prefs(tmp_path, prefs)
    loaded = load_prefs(tmp_path)
    by_id = {p.id: p for p in loaded.pages[0].placements}
    assert by_id["total_worth"].w == 16
    assert by_id["total_worth"].h == 5
    assert by_id["assets"].w == 12
    assert by_id["assets"].h == 8


def test_prefs_clamp_below_catalog_min(tmp_path: Path) -> None:
    prefs = factory_defaults()
    prefs.pages[0].placements = [Placement(id="total_worth", col=0, row=0, w=2, h=1)]
    save_prefs(tmp_path, prefs)
    loaded = load_prefs(tmp_path)
    tw = next(p for p in loaded.pages[0].placements if p.id == "total_worth")
    spec = spec_for("total_worth")
    assert spec is not None
    assert tw.w >= spec.min_w
    assert tw.h >= spec.min_h


def test_module_mins_override_round_trip(tmp_path: Path) -> None:
    prefs = factory_defaults()
    prefs.module_mins = {"total_worth": (8, 6)}
    save_prefs(tmp_path, prefs)
    loaded = load_prefs(tmp_path)
    assert loaded.module_mins["total_worth"] == (8, 6)
    eff = effective_spec("total_worth", loaded.module_mins)
    assert eff is not None
    assert eff.min_w == 8
    assert eff.min_h == 6


def test_dashboard_persist_preserves_settings_module_mins(qtbot: QtBot, tmp_path: Path) -> None:
    from tests.test_device.test_device_portfolio import _seed
    from trendalgo.device.context import open_context
    from trendalgo.device.views.portfolio_page import PortfolioPage

    profile = tmp_path / "profile"
    _seed(profile / "portfolio.db")
    ctx = open_context(profile)
    page = PortfolioPage(ctx)
    qtbot.addWidget(page)
    # Simulate Settings saving a lower min while Dashboard holds a stale empty copy.
    disk = load_prefs(ctx.root)
    disk.module_mins = {"total_worth": (4, 3)}
    save_prefs(ctx.root, disk)
    page._prefs.module_mins = {}
    page._persist()
    reloaded = load_prefs(ctx.root)
    assert reloaded.module_mins["total_worth"] == (4, 3)
    page.reload_module_mins()
    assert page._prefs.module_mins["total_worth"] == (4, 3)


def test_corrupt_prefs_fall_back(tmp_path: Path) -> None:
    (tmp_path / "portfolio_layout_prefs.json").write_text("{not-json", encoding="utf-8")
    prefs = load_prefs(tmp_path)
    assert prefs.pages[0].id == "overview"


def test_old_layout_version_resets_to_factory(tmp_path: Path) -> None:
    import json

    path = tmp_path / "portfolio_layout_prefs.json"
    path.write_text(
        json.dumps(
            {
                "layout_version": 2,
                "active_page_id": "overview",
                "grid": {"cols": 12, "rows": 24, "gap_px": 8, "magnet_px": 16},
                "pages": [{"id": "overview", "name": "Overview", "placements": []}],
            }
        ),
        encoding="utf-8",
    )
    loaded = load_prefs(tmp_path)
    assert loaded.layout_version == 3
    assert loaded.grid.cols == 24


def test_snap_magnetism() -> None:
    rect = snap_point(
        8.0,
        8.0,
        cell_w=100.0,
        cell_h=50.0,
        gap_px=8,
        magnet_px=16,
        cols=24,
        rows=12,
        w=4,
        h=3,
    )
    assert rect.col == 0
    assert rect.row == 0


def test_snap_resize_grows_and_clamps_min() -> None:
    origin = Rect(0, 0, 4, 3)
    grown = snap_resize(
        origin,
        6 * 108.0,
        4 * 58.0,
        cell_w=100.0,
        cell_h=50.0,
        gap_px=8,
        magnet_px=16,
        cols=24,
        rows=24,
        min_w=4,
        min_h=3,
        max_w=24,
        max_h=16,
    )
    assert grown.col == 0 and grown.row == 0
    assert grown.w == 6
    assert grown.h == 4
    tiny = snap_resize(
        origin,
        50.0,
        20.0,
        cell_w=100.0,
        cell_h=50.0,
        gap_px=8,
        magnet_px=16,
        cols=24,
        rows=24,
        min_w=4,
        min_h=3,
        max_w=24,
        max_h=16,
    )
    assert tiny.w == 4
    assert tiny.h == 3


def test_resize_allowed_still_detects_overlap() -> None:
    occupied = [("a", Rect(0, 0, 4, 3)), ("b", Rect(4, 0, 4, 3))]
    assert resize_allowed(Rect(0, 0, 6, 3), occupied, resizing_id="a") is False
    assert resize_allowed(Rect(0, 0, 4, 5), occupied, resizing_id="a") is True


def test_push_aside_vertical_grow() -> None:
    occupied = [
        ("a", Rect(0, 0, 6, 3)),
        ("b", Rect(0, 3, 6, 3)),
        ("c", Rect(0, 6, 6, 3)),
    ]
    layout = push_aside_for_resize("a", Rect(0, 0, 6, 5), occupied, cols=24)
    assert layout["a"] == Rect(0, 0, 6, 5)
    # Prefer right-shift when free; otherwise push below the resized module.
    assert layout["b"].col >= 6 or layout["b"].row >= 5
    ids = list(layout)
    for i, mid in enumerate(ids):
        for other in ids[i + 1 :]:
            assert not overlaps(layout[mid], layout[other])


def test_push_aside_stacks_when_no_right_room() -> None:
    occupied = [
        ("a", Rect(0, 0, 20, 3)),
        ("b", Rect(0, 3, 20, 3)),
        ("c", Rect(0, 6, 20, 3)),
    ]
    layout = push_aside_for_resize("a", Rect(0, 0, 20, 5), occupied, cols=24)
    assert layout["a"].h == 5
    assert layout["b"].row >= 5
    assert layout["c"].row >= layout["b"].bottom
    assert not overlaps(layout["a"], layout["b"])
    assert not overlaps(layout["b"], layout["c"])


def test_push_aside_horizontal_into_neighbor() -> None:
    occupied = [("a", Rect(0, 0, 4, 3)), ("b", Rect(4, 0, 4, 3))]
    layout = push_aside_for_resize("a", Rect(0, 0, 6, 3), occupied, cols=24)
    assert layout["a"].w == 6
    assert not overlaps(layout["a"], layout["b"])
    assert layout["b"].col >= 6 or layout["b"].row >= 3


def test_overlap_nudge() -> None:
    occupied = [("a", Rect(0, 0, 4, 3))]
    final, swap = find_free_or_swap(Rect(0, 0, 4, 3), occupied, moving_id="b", cols=24, rows=12)
    assert not overlaps(final, occupied[0][1]) or swap == "a"
