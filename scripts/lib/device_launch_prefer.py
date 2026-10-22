"""Resolve which TrendAlgo device binary to launch (source-first for day-to-day).

Mirrors ``scripts/packaging/launch-device.ps1``. Keep both in sync.
"""

from __future__ import annotations

from typing import Literal

Target = Literal["source", "frozen", "installed", "msi", "console"]


def prefer_device_target(
    *,
    frozen_flag: bool = False,
    source_flag: bool = False,
    keep_console: bool = False,
    has_pythonw: bool = False,
    has_python: bool = False,
    has_frozen: bool = False,
    has_installed: bool = False,
    has_msi: bool = False,
) -> Target:
    """Pick launch target. Default: pythonw source when the venv exists."""
    if keep_console:
        if not has_python:
            raise FileNotFoundError("python.exe missing for -KeepConsole")
        return "console"
    if frozen_flag:
        if has_frozen:
            return "frozen"
        if has_installed:
            return "installed"
        if has_msi:
            return "msi"
        if has_pythonw:
            return "source"
        raise FileNotFoundError("no frozen/installed/MSI device and no pythonw")
    # Source-first (default and -Source): live src/ via pythonw.
    if has_pythonw or source_flag:
        if has_pythonw:
            return "source"
        raise FileNotFoundError("pythonw.exe missing for source launch")
    if has_frozen:
        return "frozen"
    if has_installed:
        return "installed"
    if has_msi:
        return "msi"
    raise FileNotFoundError("no pythonw and no frozen/installed/MSI device")
