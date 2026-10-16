"""Windows Start-with-Windows (HKCU Run key). Pure logic + registry I/O, no Qt."""

from __future__ import annotations

import sys
from pathlib import Path

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "TrendAlgoBot"


def is_enabled() -> bool:
    if sys.platform != "win32":
        return False
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            winreg.QueryValueEx(key, VALUE_NAME)
            return True
    except OSError:
        return False


def set_enabled(enabled: bool, *, command: str | None = None) -> None:
    """Enable or disable login autostart. Windows only; no-op elsewhere."""
    if sys.platform != "win32":
        return
    import winreg

    if not enabled:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
                winreg.DeleteValue(key, VALUE_NAME)
        except OSError:
            pass
        return
    cmd = command or default_command()
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, cmd)


def default_command() -> str:
    """Prefer frozen exe; else pythonw -m trendalgo.device from repo/cwd."""
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    exe = str(pythonw if pythonw.is_file() else sys.executable)
    return f'"{exe}" -m trendalgo.device'
