"""Windows GUI hygiene: never keep a console attached to the device window.

Closing a parent console must not kill the app. Prefer pythonw / --windowed
exe / launch-device.ps1; this module is a safety net when someone starts
``python -m trendalgo.device`` from a console by mistake.
"""

from __future__ import annotations

import os
import sys


def should_detach_console(*, testing: bool = False) -> bool:
    """True when the GUI path should drop any attached console."""
    if testing:
        return False
    if os.environ.get("TRENDALGO_KEEP_CONSOLE", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }:
        return False
    return sys.platform == "win32"


def detach_console_if_needed(*, testing: bool = False) -> bool:
    """Detach from the console on Windows GUI launches. Returns True if FreeConsole ran."""
    if not should_detach_console(testing=testing):
        return False
    try:
        import ctypes

        ctypes.windll.kernel32.FreeConsole()
        return True
    except Exception:
        return False
