"""Local vs UTC display formatting."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

from trendalgo.device.profile import write_json
from trendalgo.device.settings_model import Settings, settings_to_document
from trendalgo.device.time_display import format_display_time, load_use_utc


def test_format_display_time_utc_suffix() -> None:
    dt = datetime(2026, 10, 20, 18, 5, tzinfo=UTC)
    assert format_display_time(dt, use_utc=True) == "2026-10-20 18:05 UTC"


def test_format_display_time_local_converts() -> None:
    eastern = timezone(timedelta(hours=-4))
    dt = datetime(2026, 10, 20, 18, 5, tzinfo=UTC)
    # Force path through astimezone by comparing to explicit convert.
    local_text = format_display_time(dt, use_utc=False)
    expected = dt.astimezone().strftime("%Y-%m-%d %H:%M")
    assert local_text == expected
    assert "UTC" not in local_text
    # Sanity: known offset still formats.
    assert format_display_time(dt.astimezone(eastern), use_utc=True).endswith("UTC")


def test_load_use_utc_defaults_false(tmp_path: Path) -> None:
    assert load_use_utc(tmp_path) is False
    write_json(
        tmp_path / "settings.json",
        settings_to_document(Settings("owner-1", use_utc=True)),
    )
    assert load_use_utc(tmp_path) is True


def test_settings_round_trip_use_utc() -> None:
    from trendalgo.device.settings_model import settings_from_document, validate_settings

    settings, problems = validate_settings("owner-1", "", use_utc=True)
    assert problems == []
    assert settings is not None
    assert settings.use_utc is True
    restored = settings_from_document(settings_to_document(settings))
    assert restored is not None
    assert restored.use_utc is True
    legacy = settings_from_document({"owner_id": "owner-1", "host_url": ""})
    assert legacy is not None
    assert legacy.use_utc is False
