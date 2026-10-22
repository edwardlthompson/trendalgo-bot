"""Source-first device launch preference (mirrors launch-device.ps1)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "scripts" / "lib"))

from device_launch_prefer import prefer_device_target  # noqa: E402


def test_default_prefers_pythonw_even_when_frozen_exists() -> None:
    assert prefer_device_target(has_pythonw=True, has_frozen=True, has_installed=True) == "source"


def test_frozen_flag_prefers_dist_exe() -> None:
    assert prefer_device_target(frozen_flag=True, has_pythonw=True, has_frozen=True) == "frozen"


def test_frozen_flag_falls_back_to_installed_then_source() -> None:
    assert (
        prefer_device_target(frozen_flag=True, has_pythonw=True, has_installed=True) == "installed"
    )
    assert prefer_device_target(frozen_flag=True, has_pythonw=True) == "source"


def test_keep_console_uses_python() -> None:
    assert prefer_device_target(keep_console=True, has_python=True, has_pythonw=True) == "console"


def test_source_flag_requires_pythonw() -> None:
    with pytest.raises(FileNotFoundError):
        prefer_device_target(source_flag=True, has_pythonw=False, has_frozen=True)


def test_no_venv_falls_back_to_frozen() -> None:
    assert prefer_device_target(has_pythonw=False, has_frozen=True) == "frozen"


def test_launch_script_documents_frozen_switch() -> None:
    text = (_ROOT / "scripts" / "packaging" / "launch-device.ps1").read_text(encoding="utf-8")
    assert "[switch]$Frozen" in text
    assert "$frozenExe" in text  # must not reuse $Frozen (PS case-insensitive)
    assert "Source-first" in text or "source-first" in text
    assert "relaunch-device.ps1" not in text  # relaunch is sibling helper
    relaunch = (_ROOT / "scripts" / "packaging" / "relaunch-device.ps1").read_text(encoding="utf-8")
    assert "launch-device.ps1" in relaunch
    assert "TrendAlgoDevice" in relaunch
