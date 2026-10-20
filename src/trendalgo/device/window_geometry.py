"""Persist and clamp main-window size/position under the device profile."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from trendalgo.device.profile import read_json, write_json
from trendalgo.device.ui_state import ui_state_path

_MIN_W = 480
_MIN_H = 360


@dataclass(frozen=True)
class WindowGeometry:
    x: int
    y: int
    width: int
    height: int
    maximized: bool = False


@dataclass(frozen=True)
class ScreenRect:
    x: int
    y: int
    width: int
    height: int

    @property
    def right(self) -> int:
        return self.x + self.width

    @property
    def bottom(self) -> int:
        return self.y + self.height

    def contains_point(self, px: int, py: int) -> bool:
        return self.x <= px < self.right and self.y <= py < self.bottom


def load_window_geometry(root: Path) -> WindowGeometry | None:
    """Saved main-window placement, or None on first open / corrupt data."""
    raw = read_json(ui_state_path(root))
    if not isinstance(raw, dict):
        return None
    try:
        w, h = int(raw["window_w"]), int(raw["window_h"])
        x, y = int(raw["window_x"]), int(raw["window_y"])
    except (KeyError, TypeError, ValueError):
        return None
    if w < _MIN_W or h < _MIN_H:
        return None
    return WindowGeometry(x, y, w, h, _as_bool(raw.get("window_maximized")))


def save_window_geometry_values(root: Path, geom: WindowGeometry) -> None:
    """Persist geometry fields merged into ui_state.json."""
    previous = read_json(ui_state_path(root)) or {}
    if not isinstance(previous, dict):
        previous = {}
    previous.update(
        {
            "window_x": int(geom.x),
            "window_y": int(geom.y),
            "window_w": max(_MIN_W, int(geom.width)),
            "window_h": max(_MIN_H, int(geom.height)),
            "window_maximized": bool(geom.maximized),
        }
    )
    write_json(ui_state_path(root), previous)


def clamp_window_geometry(
    geom: WindowGeometry,
    screens: list[ScreenRect],
    *,
    min_w: int = _MIN_W,
    min_h: int = _MIN_H,
) -> WindowGeometry:
    """Keep the window on a visible screen and enforce a corner-dock floor size."""
    width, height = max(min_w, int(geom.width)), max(min_h, int(geom.height))
    x, y = int(geom.x), int(geom.y)
    if not screens:
        return WindowGeometry(x, y, width, height, geom.maximized)
    host = next((s for s in screens if s.contains_point(x, y)), None)
    if host is None:
        host = next((s for s in screens if _hit(x, y, width, height, s)), screens[0])
        x, y = host.x, host.y
    x = min(max(x, host.x), max(host.x, host.right - width))
    y = min(max(y, host.y), max(host.y, host.bottom - height))
    return WindowGeometry(x, y, min(width, host.width), min(height, host.height), geom.maximized)


def save_window_geometry(root: Path, widget: Any) -> None:
    """Snapshot a Qt main window into the profile."""
    previous = load_window_geometry(root)
    if bool(widget.isMaximized()):
        base = previous or WindowGeometry(
            int(widget.x()),
            int(widget.y()),
            max(_MIN_W, int(widget.width())),
            max(_MIN_H, int(widget.height())),
        )
        save_window_geometry_values(
            root, WindowGeometry(base.x, base.y, base.width, base.height, True)
        )
        return
    frame = widget.frameGeometry()
    save_window_geometry_values(
        root,
        WindowGeometry(
            int(frame.x()),
            int(frame.y()),
            max(_MIN_W, int(frame.width())),
            max(_MIN_H, int(frame.height())),
        ),
    )


def restore_window_geometry(root: Path, widget: Any) -> bool:
    """Apply saved geometry to a Qt widget. Returns False when nothing to restore."""
    saved = load_window_geometry(root)
    if saved is None:
        return False
    clamped = clamp_window_geometry(saved, _qt_screens())
    widget.setGeometry(clamped.x, clamped.y, clamped.width, clamped.height)
    if clamped.maximized:
        widget.showMaximized()
    return True


def _qt_screens() -> list[ScreenRect]:
    try:
        from PySide6.QtGui import QGuiApplication
    except ImportError:
        return []
    app = QGuiApplication.instance()
    if app is None:
        return []
    return [
        ScreenRect(r.x(), r.y(), r.width(), r.height())
        for r in (s.availableGeometry() for s in app.screens())
    ]


def _hit(x: int, y: int, w: int, h: int, screen: ScreenRect) -> bool:
    return not (x + w <= screen.x or x >= screen.right or y + h <= screen.y or y >= screen.bottom)


def _as_bool(raw: Any) -> bool:
    if isinstance(raw, bool):
        return raw
    return isinstance(raw, str) and raw.strip().lower() in {"1", "true", "yes", "on"}
