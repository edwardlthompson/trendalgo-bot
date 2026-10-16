"""Icons for the device app: one 24-unit stroke family for the tabs, and the brand artwork.

The glyph strokes take their color at draw time, so light and dark modes both read clearly.
Brand artwork comes from `design_tokens.BRAND_MARK_SVG` (generated from the logo SVG) and from
the committed app icon PNG when it is on disk (dev checkout, or bundled by PyInstaller).
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from trendalgo.device import design_tokens as T

NAV_GLYPHS: dict[str, str] = {
    "portfolio": (
        '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/>'
        '<rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>'
    ),
    "bot": (
        '<rect x="5" y="8" width="14" height="11" rx="3"/><path d="M12 4v4"/>'
        '<circle cx="9.5" cy="13.5" r="1"/><circle cx="14.5" cy="13.5" r="1"/>'
    ),
    "scanner": '<circle cx="11" cy="11" r="6.5"/><path d="M16 16l4.5 4.5"/>',
    "backtest": '<path d="M3 3v18h18"/><path d="M7 15l4-4 3 3 6-7"/>',
    "plan": (
        '<rect x="5" y="4" width="14" height="17" rx="2"/><path d="M9 4h6v3H9z"/>'
        '<path d="M9 12h6M9 16h4"/>'
    ),
    "settings": (
        '<path d="M4 7h10M18 7h2M4 17h2M10 17h10"/><circle cx="16" cy="7" r="2"/>'
        '<circle cx="8" cy="17" r="2"/>'
    ),
    "more": (
        '<circle cx="5" cy="12" r="1.5"/><circle cx="12" cy="12" r="1.5"/>'
        '<circle cx="19" cy="12" r="1.5"/>'
    ),
    "glossary": '<path d="M5 4h11a2 2 0 012 2v14l-4-2-4 2-4-2-4 2V6a2 2 0 012-2z"/>',
    "alerts": ('<path d="M6 8a6 6 0 0112 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10 21a2 2 0 004 0"/>'),
    "export": '<path d="M12 3v12"/><path d="M8 11l4 4 4-4"/><path d="M5 19h14"/>',
    # Universal share (nodes + links), used on Backtest / Portfolio export actions.
    "share": (
        '<circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/>'
        '<path d="M8.59 13.51l6.83 3.98M15.41 6.51l-6.82 3.98"/>'
    ),
    "billing": (
        '<rect x="3" y="6" width="18" height="12" rx="2"/><path d="M3 10h18"/><path d="M7 15h2"/>'
    ),
    "debug": (
        '<path d="M8 9V7a4 4 0 018 0v2"/><rect x="6" y="9" width="12" height="11" rx="2"/>'
        '<path d="M10 13h4M10 16h2"/>'
    ),
    "research": (
        '<path d="M4 19V5"/><path d="M4 15l4-4 3 3 5-6 4 4"/><circle cx="18" cy="6" r="2"/>'
    ),
    "ai": (
        '<path d="M12 3l1.5 4.5L18 9l-4.5 1.5L12 15l-1.5-4.5L6 9l4.5-1.5z"/>'
        '<path d="M5 19h14"/><path d="M8 19v-3M16 19v-3"/>'
    ),
}
APP_ICON_FILE = "app-icon-192.png"
APP_ICON_ICO = "app-icon.ico"
SPLASH_FILE = "splash-1280x720.png"
WINDOWS_APP_ID = "TrendAlgo.Bot.Device"


def set_windows_app_id(app_id: str = WINDOWS_APP_ID) -> None:
    """Win32: group the taskbar under our id so the icon is not python.exe."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        from typing import Any, cast

        shell32 = cast(Any, ctypes.windll.shell32)
        shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except (AttributeError, OSError):
        return


def nav_icon(name: str, color: str, size: int = 20) -> QIcon:
    """A tab glyph in one color. An unknown name draws nothing rather than failing."""
    glyph = NAV_GLYPHS.get(name, "")
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        f'stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        f"{glyph}</svg>"
    )
    return QIcon(render_svg(svg, size))


def brand_mark(size: int) -> QPixmap:
    return render_svg(T.BRAND_MARK_SVG, size)


def window_icon() -> QIcon:
    """The app icon for the window and taskbar. Prefer ICO, then PNG, then the flat mark."""
    for folder in _asset_folders():
        for name in (APP_ICON_ICO, APP_ICON_FILE):
            candidate = folder / name
            if candidate.is_file():
                return QIcon(str(candidate))
    return QIcon(brand_mark(64))


def splash_pixmap() -> QPixmap | None:
    """Cold-start splash art, or None when the PNG is not on disk."""
    for folder in _asset_folders():
        candidate = folder / SPLASH_FILE
        if candidate.is_file():
            return QPixmap(str(candidate))
    return None


def render_svg(svg: str, size: int) -> QPixmap:
    """Draw an SVG string into a transparent square pixmap. Invalid SVG gives a blank pixmap."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    if not renderer.isValid():
        return pixmap
    painter = QPainter(pixmap)
    renderer.render(painter, QRectF(0, 0, size, size))
    painter.end()
    return pixmap


def _asset_folders() -> list[Path]:
    folders: list[Path] = []
    bundled = getattr(sys, "_MEIPASS", None)
    if isinstance(bundled, str):
        folders.append(Path(bundled) / "branding" / "assets")
    folders.append(Path(__file__).resolve().parents[3] / "branding" / "assets")
    return folders
