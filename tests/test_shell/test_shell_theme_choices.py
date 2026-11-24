"""AV-G-STR4 / AV-G-SET3 — theme/accent choices match PySide + ShellTheme.cs."""

from __future__ import annotations

from pathlib import Path

from trendalgo.device import design_tokens as T
from trendalgo.device.settings_model import ACCENT_CHOICES, THEME_CHOICES

_SHELL_THEME = (
    Path(__file__).resolve().parents[2] / "shell" / "TrendAlgo.Shell" / "Services" / "ShellTheme.cs"
)


def test_theme_choices_system_light_dark() -> None:
    assert THEME_CHOICES == ("system", "light", "dark")


def test_accent_presets_include_hex_list() -> None:
    assert "" in ACCENT_CHOICES
    for hex_color in T.ACCENT_PRESETS:
        assert hex_color in ACCENT_CHOICES
    assert "#2563eb" in ACCENT_CHOICES


def test_shell_theme_cs_mirrors_pyside_choices() -> None:
    text = _SHELL_THEME.read_text(encoding="utf-8")
    assert '["system", "light", "dark"]' in text
    assert '""' in text  # default accent slot
    for hex_color in T.ACCENT_PRESETS:
        assert hex_color in text
