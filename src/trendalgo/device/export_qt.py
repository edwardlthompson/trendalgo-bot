"""QApplication bootstrap for headless PNG share (fonts + dark theme under offscreen)."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

_QT_APP: Any = None
_FONTS_PINNED = False


def ensure_export_qapp(
    root: Path | None = None,
    *,
    force_dark: bool = True,
) -> Any:
    """Return a QApplication ready for widget.grab() PNG export.

    Windows ``offscreen`` ships with an empty font database (tofu glyphs). We register
    system TTFs. Avalonia invokes us headless with no prior ``apply_theme``, so exports
    defaulted to light — force dark to match the product share cards.
    """
    global _QT_APP
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    created = False
    if app is None:
        _QT_APP = QApplication([])
        app = _QT_APP
        created = True

    pin_export_fonts()
    if created or force_dark:
        from trendalgo.device.theme import apply_theme

        accent = _accent_from_root(root) if root is not None else ""
        apply_theme(app, "dark" if force_dark else "system", accent)
    return app


def pin_export_fonts() -> None:
    """Register Windows (or Linux) UI fonts when the QPA font DB is empty."""
    global _FONTS_PINNED
    if _FONTS_PINNED:
        return
    from PySide6.QtGui import QFont, QFontDatabase
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        return
    if QFontDatabase.families():
        _FONTS_PINNED = True
        return
    for path in _candidate_font_files():
        if path.is_file():
            QFontDatabase.addApplicationFont(str(path))
    families = list(QFontDatabase.families())
    pick = next(
        (f for f in ("Segoe UI", "Arial", "DejaVu Sans", "Noto Sans", "FreeSans") if f in families),
        families[0] if families else "",
    )
    if pick:
        font = app.font()
        font.setFamily(pick)
        if font.pointSize() <= 0:
            font.setPointSize(10)
        app.setFont(QFont(pick, max(10, font.pointSize())))
    _FONTS_PINNED = True


def _candidate_font_files() -> list[Path]:
    out: list[Path] = []
    if sys.platform == "win32":
        windir = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
        for name in (
            "segoeui.ttf",
            "segoeuib.ttf",
            "arial.ttf",
            "arialbd.ttf",
            "tahoma.ttf",
            "calibri.ttf",
        ):
            out.append(windir / name)
        return out
    for folder in (
        Path("/usr/share/fonts/truetype/dejavu"),
        Path("/usr/share/fonts/truetype/liberation"),
        Path("/usr/share/fonts/TTF"),
    ):
        for name in (
            "DejaVuSans.ttf",
            "DejaVuSans-Bold.ttf",
            "LiberationSans-Regular.ttf",
            "NotoSans-Regular.ttf",
        ):
            out.append(folder / name)
    return out


def _accent_from_root(root: Path) -> str:
    try:
        from trendalgo.device.profile import ProfileError, read_json
        from trendalgo.device.settings_model import settings_from_document

        settings = settings_from_document(read_json(root / "settings.json"))
        return settings.accent if settings is not None else ""
    except (OSError, ProfileError, TypeError, ValueError):
        return ""
