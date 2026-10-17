"""Locked Settings IA order for Settings-only chrome (ADR-0004 / GP-5)."""

from __future__ import annotations

SETTINGS_SECTION_ORDER: tuple[str, ...] = (
    "appearance",
    "dashboard",
    "privacy",
    "data",
    "about",
)


def settings_section_order() -> tuple[str, ...]:
    return SETTINGS_SECTION_ORDER
