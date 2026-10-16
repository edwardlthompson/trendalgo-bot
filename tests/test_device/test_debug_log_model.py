"""Device log tail helper."""

from __future__ import annotations

from pathlib import Path

from trendalgo.device.debug_log_model import device_log_path, tail_device_log
from trendalgo.device.profile import DEVICE_LOG


def test_tail_returns_empty_when_missing(tmp_path: Path) -> None:
    root = tmp_path / "profile"
    root.mkdir()
    assert tail_device_log(root) == []
    assert device_log_path(root).name == DEVICE_LOG


def test_tail_keeps_last_lines(tmp_path: Path) -> None:
    root = tmp_path / "profile"
    root.mkdir()
    path = root / DEVICE_LOG
    path.write_text("\n".join(f"line-{i}" for i in range(250)), encoding="utf-8")
    lines = tail_device_log(root, max_lines=10)
    assert len(lines) == 10
    assert lines[0] == "line-240"
    assert lines[-1] == "line-249"
