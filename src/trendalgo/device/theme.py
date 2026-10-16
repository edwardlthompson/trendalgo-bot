"""Qt side of the look: Fusion style, palette, body font, and the stylesheet. Qt is imported here only.

The colors come from `theme_css` (pure) and `design_tokens` (generated). Call `apply_theme` once
at start and again after the owner saves a new theme or accent.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QGuiApplication, QPalette
from PySide6.QtWidgets import QApplication

from trendalgo.device.theme_css import (
    Mode,
    body_point_size,
    build_stylesheet,
    colors_for,
    resolve_mode,
)

_ACTIVE: Mode = "light"


def active_mode() -> Mode:
    """The mode last painted by `apply_theme`. Icons read it to pick their color."""
    return _ACTIVE


def system_prefers_dark() -> bool:
    return QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark


def apply_theme(app: QApplication, choice: str = "system", accent: str = "") -> Mode:
    """Paint the whole app. `choice` is system, light, or dark; `accent` is a preset or empty."""
    global _ACTIVE
    mode = resolve_mode(choice, system_prefers_dark())
    # Set first: setPalette sends PaletteChange at once, and the icons read the active mode then.
    _ACTIVE = mode
    colors = colors_for(mode, accent)
    app.setStyle("Fusion")
    app.setPalette(_palette(colors))
    font = app.font()
    font.setPointSizeF(body_point_size())
    app.setFont(font)
    app.setStyleSheet(build_stylesheet(mode, accent))
    return mode


def _palette(colors: dict[str, str]) -> QPalette:
    palette = QPalette()
    roles = {
        QPalette.ColorRole.Window: colors["background"],
        QPalette.ColorRole.WindowText: colors["onBackground"],
        QPalette.ColorRole.Base: colors["background"],
        QPalette.ColorRole.AlternateBase: colors["surface"],
        QPalette.ColorRole.Text: colors["onBackground"],
        QPalette.ColorRole.Button: colors["surfaceVariant"],
        QPalette.ColorRole.ButtonText: colors["onSurfaceVariant"],
        QPalette.ColorRole.Highlight: colors["primaryContainer"],
        QPalette.ColorRole.HighlightedText: colors["onPrimaryContainer"],
        QPalette.ColorRole.PlaceholderText: colors["onSurfaceVariant"],
        QPalette.ColorRole.ToolTipBase: colors["surface"],
        QPalette.ColorRole.ToolTipText: colors["onSurface"],
        QPalette.ColorRole.Link: colors["primary"],
    }
    for role, value in roles.items():
        palette.setColor(role, QColor(value))
    disabled = QColor(colors["outline"])
    for role in (
        QPalette.ColorRole.WindowText,
        QPalette.ColorRole.Text,
        QPalette.ColorRole.ButtonText,
    ):
        palette.setColor(QPalette.ColorGroup.Disabled, role, disabled)
    return palette
