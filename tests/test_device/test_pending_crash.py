"""Crash-capture queue: sanitize, opt-in persist, clear when save-crashes turns off."""

from __future__ import annotations

from pathlib import Path

from trendalgo.device.crash_capture.pending_crash import (
    clear_pending_crash,
    on_save_crashes_changed,
    persist_pending_crash,
    read_pending_crash,
    reset_session_for_tests,
    sanitize_crash_payload,
)
from trendalgo.device.crash_capture.save_crashes import set_save_crashes


def test_sanitizes_before_persist_and_queues_one_record(tmp_path: Path) -> None:
    reset_session_for_tests()
    set_save_crashes(tmp_path, True)
    persist_pending_crash(
        tmp_path,
        {
            "message": "boom ghp_abcdefghijklmnopqrstuvwxyz012345",
            "stack": r"at C:\Users\Ada\x.py",
        },
    )
    read = read_pending_crash(tmp_path)
    assert read is not None
    assert "ghp_" not in read.message
    assert "Ada" not in read.stack


def test_drops_extra_keys_from_payload_allowlist() -> None:
    got = sanitize_crash_payload(
        {
            "message": "e",
            "stack": "s",
            "email": "keep-out",
            "token": "keep-out",
            "prompt": "keep-out",
        }
    )
    assert set(got.__dataclass_fields__) == {"message", "stack"}
    assert "keep-out" not in got.message
    assert "keep-out" not in got.stack


def test_does_not_write_local_file_unless_save_local(tmp_path: Path) -> None:
    reset_session_for_tests()
    persist_pending_crash(tmp_path, {"message": "e", "stack": "s"}, save_local=False)
    assert not (tmp_path / "pending_crash.json").is_file()
    assert read_pending_crash(tmp_path) is not None  # session only


def test_clears_when_save_crashes_turns_off(tmp_path: Path) -> None:
    reset_session_for_tests()
    persist_pending_crash(tmp_path, {"message": "e", "stack": "s"}, save_local=True)
    on_save_crashes_changed(tmp_path, False)
    assert read_pending_crash(tmp_path) is None
    clear_pending_crash(tmp_path)
