"""Tail the device log file under the profile folder."""

from __future__ import annotations

from pathlib import Path

from trendalgo.device.profile import DEVICE_LOG

DEFAULT_TAIL_LINES = 200


def device_log_path(profile_root: Path) -> Path:
    return profile_root / DEVICE_LOG


def tail_device_log(profile_root: Path, *, max_lines: int = DEFAULT_TAIL_LINES) -> list[str]:
    path = device_log_path(profile_root)
    if not path.is_file():
        return []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    lines = text.splitlines()
    if max_lines <= 0:
        return lines
    return lines[-max_lines:]
