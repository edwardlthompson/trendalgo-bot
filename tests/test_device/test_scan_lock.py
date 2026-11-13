"""Only one Opportunity scan_job may hold the profile lock."""

from __future__ import annotations

from pathlib import Path

import pytest

from trendalgo.device.scan_lock import (
    ScanBusyError,
    scan_lock_held,
    try_acquire_scan_lock,
)


def test_second_acquire_raises(tmp_path: Path) -> None:
    first = try_acquire_scan_lock(tmp_path)
    try:
        assert scan_lock_held(tmp_path) is True
        with pytest.raises(ScanBusyError):
            try_acquire_scan_lock(tmp_path)
    finally:
        first.release()
    assert scan_lock_held(tmp_path) is False


def test_scan_job_busy_when_lock_held(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from trendalgo.device.scan_job import scan_job

    held = try_acquire_scan_lock(tmp_path)
    try:
        with pytest.raises(ScanBusyError):
            scan_job(tmp_path)
    finally:
        held.release()
