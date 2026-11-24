"""AV-G-SET7 — privacy / data / updates settings surfaces."""

from __future__ import annotations

from pathlib import Path

from trendalgo.device.crash_capture.save_crashes import get_save_crashes
from trendalgo.device.export_prefs import load_export_prefs
from trendalgo.device.profile import SETTINGS_FILE
from trendalgo.results_store.desk_settings_misc import (
    apply_data_settings,
    apply_privacy_settings,
    load_data_surface,
    load_privacy_surface,
    load_updates_surface,
)


def test_privacy_roundtrip(tmp_path: Path) -> None:
    assert get_save_crashes(tmp_path) is False
    result = apply_privacy_settings(tmp_path, {"save_crashes": True})
    assert result["ok"] is True
    assert result["save_crashes"] is True
    assert get_save_crashes(tmp_path) is True
    loaded = load_privacy_surface(tmp_path)
    assert loaded["label"]
    assert loaded["help"]


def test_data_export_and_utc(tmp_path: Path) -> None:
    (tmp_path / SETTINGS_FILE).write_text(
        '{"owner_id":"desk","theme":"system","accent":"","use_utc":false}',
        encoding="utf-8",
    )
    export = tmp_path / "my-exports"
    export.mkdir()
    result = apply_data_settings(
        tmp_path,
        {"last_export_dir": str(export), "use_utc": True},
    )
    assert result["ok"] is True
    assert result["use_utc"] is True
    assert load_export_prefs(tmp_path).last_export_dir == str(export)
    loaded = load_data_surface(tmp_path)
    assert loaded["help"]
    assert loaded["use_utc"] is True


def test_updates_surface_has_version(tmp_path: Path) -> None:
    data = load_updates_surface(tmp_path)
    assert data["ok"] is True
    assert data["version"]
    assert data["check_label"]
    assert data["changelog_url"]
