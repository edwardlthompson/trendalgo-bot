"""Look rules, pure (no Qt): mode choice, accent presets, the stylesheet, and text contrast."""

from __future__ import annotations

import pytest

from trendalgo.device import design_tokens as T
from trendalgo.device.theme_css import (
    Mode,
    body_point_size,
    build_stylesheet,
    colors_for,
    contrast_ratio,
    resolve_mode,
)

TEXT_PAIRS = (
    ("onBackground", "background"),
    ("onSurface", "surface"),
    ("onSurfaceVariant", "background"),
    ("onSurfaceVariant", "surface"),
    ("onSurfaceVariant", "surfaceVariant"),
    ("onPrimaryContainer", "primaryContainer"),
    ("onSecondaryContainer", "secondaryContainer"),
    ("error", "background"),
)


def test_an_explicit_choice_wins_over_the_os() -> None:
    assert resolve_mode("light", system_is_dark=True) == "light"
    assert resolve_mode("dark", system_is_dark=False) == "dark"


def test_system_follows_the_os_and_an_unknown_choice_does_too() -> None:
    assert resolve_mode("system", system_is_dark=True) == "dark"
    assert resolve_mode("system", system_is_dark=False) == "light"
    assert resolve_mode("sepia", system_is_dark=True) == "dark"


def test_each_mode_uses_its_own_palette() -> None:
    assert colors_for("light")["background"] == T.LIGHT["background"]
    assert colors_for("dark")["background"] == T.DARK["background"]


def test_an_accent_replaces_only_primary_and_only_a_listed_preset() -> None:
    base = colors_for("light")
    accent = T.ACCENT_PRESETS[0]
    chosen = colors_for("light", accent)
    assert chosen["primary"] == accent
    assert {k: v for k, v in chosen.items() if k != "primary"} == {
        k: v for k, v in base.items() if k != "primary"
    }
    assert colors_for("light", "#123456") == base


@pytest.mark.parametrize("mode", ["light", "dark"])
@pytest.mark.parametrize("accent", ["", *T.ACCENT_PRESETS])
def test_the_stylesheet_resolves_every_placeholder(mode: Mode, accent: str) -> None:
    sheet = build_stylesheet(mode, accent)
    assert "$" not in sheet
    assert colors_for(mode, accent)["primary"] in sheet
    assert 'QPushButton[role="primary"]' in sheet
    assert "QTabBar::tab:selected" in sheet


@pytest.mark.parametrize("mode", ["light", "dark"])
@pytest.mark.parametrize(("text", "background"), TEXT_PAIRS)
def test_text_meets_the_aa_contrast_floor(mode: Mode, text: str, background: str) -> None:
    colors = colors_for(mode)
    assert contrast_ratio(colors[text], colors[background]) >= 4.5


def test_contrast_ratio_matches_the_wcag_extremes() -> None:
    assert round(contrast_ratio("#000000", "#FFFFFF"), 1) == 21.0
    assert contrast_ratio("#FFFFFF", "#FFFFFF") == 1.0


def test_body_text_is_fourteen_pixels_at_96_dpi() -> None:
    assert body_point_size() == pytest.approx(10.5)
