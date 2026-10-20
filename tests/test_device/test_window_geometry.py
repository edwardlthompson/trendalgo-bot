"""Main-window geometry persistence and off-screen clamp."""

from __future__ import annotations

from pathlib import Path

from trendalgo.device.profile import write_json
from trendalgo.device.ui_state import save_nav_page, ui_state_path
from trendalgo.device.window_geometry import (
    ScreenRect,
    WindowGeometry,
    clamp_window_geometry,
    load_window_geometry,
    save_window_geometry_values,
)


def test_save_and_load_window_geometry(tmp_path: Path) -> None:
    geom = WindowGeometry(x=120, y=80, width=900, height=600, maximized=False)
    save_window_geometry_values(tmp_path, geom)
    loaded = load_window_geometry(tmp_path)
    assert loaded == geom


def test_geometry_merges_with_nav_page(tmp_path: Path) -> None:
    save_nav_page(tmp_path, 0)
    save_window_geometry_values(
        tmp_path, WindowGeometry(x=10, y=20, width=800, height=500, maximized=True)
    )
    loaded = load_window_geometry(tmp_path)
    assert loaded is not None
    assert loaded.maximized is True
    assert loaded.width == 800
    raw = (tmp_path / "ui_state.json").read_text(encoding="utf-8")
    assert "nav_page" in raw


def test_corrupt_or_tiny_geometry_ignored(tmp_path: Path) -> None:
    write_json(
        ui_state_path(tmp_path), {"window_w": 100, "window_h": 100, "window_x": 0, "window_y": 0}
    )
    assert load_window_geometry(tmp_path) is None
    write_json(ui_state_path(tmp_path), {"window_w": "nope"})
    assert load_window_geometry(tmp_path) is None


def test_clamp_moves_offscreen_onto_primary() -> None:
    screens = [ScreenRect(x=0, y=0, width=1920, height=1080)]
    geom = WindowGeometry(x=-5000, y=-4000, width=800, height=500)
    clamped = clamp_window_geometry(geom, screens)
    assert clamped.x == 0
    assert clamped.y == 0
    assert clamped.width == 800
    assert clamped.height == 500


def test_clamp_enforces_minimum_size() -> None:
    screens = [ScreenRect(x=0, y=0, width=1920, height=1080)]
    geom = WindowGeometry(x=10, y=10, width=100, height=80)
    clamped = clamp_window_geometry(geom, screens)
    assert clamped.width >= 480
    assert clamped.height >= 360


def test_clamp_keeps_point_on_second_monitor() -> None:
    screens = [
        ScreenRect(x=0, y=0, width=1920, height=1080),
        ScreenRect(x=1920, y=0, width=1600, height=900),
    ]
    geom = WindowGeometry(x=2000, y=40, width=700, height=500)
    clamped = clamp_window_geometry(geom, screens)
    assert clamped.x >= 1920
    assert clamped.x < 1920 + 1600
