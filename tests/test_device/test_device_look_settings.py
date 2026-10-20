"""The saved look in settings.json (pure, no Qt): validation, reading, and defaults for old files."""

from __future__ import annotations

import pytest

from trendalgo.device import design_tokens as T
from trendalgo.device import strings as S
from trendalgo.device.profile import ProfileError
from trendalgo.device.settings_model import (
    ACCENT_CHOICES,
    Settings,
    settings_from_document,
    settings_to_document,
    validate_settings,
)


def test_the_look_is_saved_with_the_owner_and_the_host() -> None:
    settings, problems = validate_settings(" owner-1 ", "", "DARK", "#2563EB")
    assert problems == []
    assert settings == Settings("owner-1", "", "", "dark", "#2563eb")
    assert settings_to_document(settings) == {
        "owner_id": "owner-1",
        "host_url": "",
        "theme": "dark",
        "accent": "#2563eb",
        "use_utc": False,
    }


def test_the_form_refuses_an_unknown_theme_and_accent() -> None:
    settings, problems = validate_settings("owner-1", "", "sepia", "#123456")
    assert settings is None
    assert any(problem.startswith("Theme:") for problem in problems)
    assert any(problem.startswith("Accent color:") for problem in problems)


def test_an_old_file_without_the_look_reads_as_the_default() -> None:
    settings = settings_from_document({"owner_id": "owner-1", "host_url": ""})
    assert settings == Settings("owner-1", "", "", "system", "")


def test_a_bad_look_value_reads_as_the_default_so_a_plan_can_still_save() -> None:
    document = {"owner_id": "owner-1", "host_url": "", "theme": 3, "accent": "#123456"}
    assert settings_from_document(document) == Settings("owner-1", "", "", "system", "")


def test_a_bad_owner_still_refuses_to_load() -> None:
    with pytest.raises(ProfileError):
        settings_from_document({"owner_id": "bad owner!", "host_url": "", "theme": "dark"})


def test_the_accent_choices_are_the_default_then_the_five_presets() -> None:
    assert ACCENT_CHOICES == ("", *T.ACCENT_PRESETS)
    assert len(S.ACCENT_NAMES) == len(T.ACCENT_PRESETS)
