"""Profile folder: paths, atomic JSON writes, and clear errors for corrupt files."""

from __future__ import annotations

from pathlib import Path

import pytest

from trendalgo.device import profile
from trendalgo.device.context import open_context
from trendalgo.device.profile import (
    CANDLES_DB,
    CANDLES_ENV,
    DEFAULT_PROFILE,
    PROFILE_ENV,
    ProfileError,
    db_paths,
    profile_dir,
    read_json,
    write_json,
)


def test_profile_dir_uses_the_env_var_then_the_default(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv(PROFILE_ENV, str(tmp_path))
    assert profile_dir() == tmp_path
    monkeypatch.delenv(PROFILE_ENV)
    assert profile_dir() == DEFAULT_PROFILE


def test_candle_path_can_point_at_the_main_app_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    assert db_paths(tmp_path)["candles"] == tmp_path / CANDLES_DB
    monkeypatch.setenv(CANDLES_ENV, str(tmp_path / "elsewhere.db"))
    assert db_paths(tmp_path)["candles"] == tmp_path / "elsewhere.db"


def test_open_context_creates_the_folder_and_names_every_file(tmp_path: Path) -> None:
    root = tmp_path / "new" / "profile"
    ctx = open_context(root)
    assert root.is_dir()
    assert ctx.settings_path == root / "settings.json"
    assert ctx.plan_path == root / "plan.json"
    assert ctx.lock_path == root / "device.lock"
    assert set(ctx.databases) == {"scanner", "bots", "journal", "candles"}


def test_read_json_returns_none_for_a_missing_file(tmp_path: Path) -> None:
    assert read_json(tmp_path / "absent.json") is None


def test_read_json_refuses_corrupt_and_non_object_content(tmp_path: Path) -> None:
    corrupt = tmp_path / "bad.json"
    corrupt.write_text("{not json", encoding="utf-8")
    with pytest.raises(ProfileError, match="bad.json cannot be read"):
        read_json(corrupt)
    listed = tmp_path / "list.json"
    listed.write_text("[1, 2]", encoding="utf-8")
    with pytest.raises(ProfileError, match="must hold a JSON object"):
        read_json(listed)


def test_write_json_creates_folders_and_round_trips(tmp_path: Path) -> None:
    target = tmp_path / "a" / "b" / "settings.json"
    write_json(target, {"owner_id": "owner-1"})
    assert read_json(target) == {"owner_id": "owner-1"}


def test_a_failed_write_keeps_the_old_file_and_leaves_no_temp_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "plan.json"
    write_json(target, {"plan_version": 1})

    def disk_full(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("disk full")

    monkeypatch.setattr(profile.json, "dump", disk_full)
    with pytest.raises(RuntimeError, match="disk full"):
        write_json(target, {"plan_version": 2})
    assert read_json(target) == {"plan_version": 1}
    assert list(tmp_path.glob("*.tmp")) == []
