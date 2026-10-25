"""Windows: keep multiprocessing spawn workers from flashing console windows.

CPython (bpo-35797) rewrites venv spawn targets to ``sys._base_executable``,
which is console ``python.exe`` even when the GUI was started via ``pythonw``.
OR ``CREATE_NO_WINDOW`` onto those CreateProcess calls.
"""

from __future__ import annotations

import sys

_CREATE_NO_WINDOW = 0x08000000
_PATCHED = False


def install_spawn_no_console() -> bool:
    """Patch spawn Popen on win32. Idempotent. Returns True if patched."""
    global _PATCHED
    if _PATCHED or sys.platform != "win32":
        return _PATCHED
    try:
        import _winapi
        from multiprocessing import popen_spawn_win32 as psw
    except ImportError:
        return False

    orig_init = psw.Popen.__init__

    def _init(self, process_obj):  # noqa: ANN001
        real = _winapi.CreateProcess

        def create(app_name, cmd_line, *args):  # noqa: ANN001
            args_list = list(args)
            if len(args_list) >= 4:
                args_list[3] = int(args_list[3] or 0) | _CREATE_NO_WINDOW
            return real(app_name, cmd_line, *args_list)

        _winapi.CreateProcess = create  # type: ignore[assignment]
        try:
            return orig_init(self, process_obj)
        finally:
            _winapi.CreateProcess = real  # type: ignore[assignment]

    psw.Popen.__init__ = _init  # type: ignore[method-assign]
    _PATCHED = True
    return True
