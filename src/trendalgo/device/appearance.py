"""Saved look: the theme and accent from settings.json, applied at start and when the OS changes."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication

from trendalgo.device.context import DeviceContext
from trendalgo.device.profile import ProfileError, read_json
from trendalgo.device.settings_model import settings_from_document
from trendalgo.device.theme import apply_theme

DEFAULT_CHOICE = ("system", "")


def saved_appearance(ctx: DeviceContext) -> tuple[str, str]:
    """(theme, accent) from settings.json. Missing or unreadable settings give the defaults."""
    try:
        settings = settings_from_document(read_json(ctx.settings_path))
    except ProfileError:
        return DEFAULT_CHOICE
    if settings is None:
        return DEFAULT_CHOICE
    return settings.theme, settings.accent


def apply_saved_appearance(app: QApplication, ctx: DeviceContext) -> None:
    theme, accent = saved_appearance(ctx)
    apply_theme(app, theme, accent)


def follow_color_scheme(app: QApplication, ctx: DeviceContext) -> None:
    """Re-apply the saved look when Windows switches between light and dark."""

    def _changed(_scheme: object) -> None:
        apply_saved_appearance(app, ctx)

    app.styleHints().colorSchemeChanged.connect(_changed)
