"""Settings-only chrome: locked IA order; header has no theme/About/donate."""

from __future__ import annotations

from trendalgo.device.settings_chrome import SETTINGS_SECTION_ORDER, settings_section_order
from trendalgo.device.views import chrome as chrome_mod


def test_settings_section_order_is_locked() -> None:
    assert settings_section_order() == (
        "appearance",
        "dashboard",
        "privacy",
        "data",
        "about",
    )
    assert SETTINGS_SECTION_ORDER == settings_section_order()


def test_brand_header_source_has_no_theme_about_or_donate_actions() -> None:
    source = chrome_mod.__file__
    assert source is not None
    text = open(source, encoding="utf-8").read()  # noqa: PTH123
    assert "THEME" not in text
    assert "DONATE" not in text
    assert "ABOUT" not in text
    assert "Settings" not in text  # Settings lives in the nav tab, not BrandHeader
