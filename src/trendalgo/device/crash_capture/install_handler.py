"""Install process-wide crash hooks. Opt-in only; never re-enter on handler errors."""

from __future__ import annotations

import sys
import threading
import traceback
from collections.abc import Callable
from pathlib import Path
from types import TracebackType

from trendalgo.device.crash_capture.pending_crash import persist_pending_crash

_installed = False
_prev_hook: Callable[[type[BaseException], BaseException, TracebackType | None], None] | None
_prev_hook = None
_prev_thread: Callable[[threading.ExceptHookArgs], None] | None = None


def install_crash_handler(root: Path, opt_in: Callable[[], bool]) -> None:
    global _installed, _prev_hook, _prev_thread
    if _installed:
        return
    _installed = True
    _prev_hook = sys.excepthook
    _prev_thread = threading.excepthook

    def store(message: str, stack: str) -> None:
        if not opt_in():
            return
        try:
            persist_pending_crash(root, {"message": message, "stack": stack})
        except Exception:  # noqa: BLE001 — never re-enter
            return

    def hook(
        exc_type: type[BaseException],
        exc: BaseException,
        tb: TracebackType | None,
    ) -> None:
        store(str(exc) or exc_type.__name__, "".join(traceback.format_exception(exc_type, exc, tb)))
        if _prev_hook is not None:
            _prev_hook(exc_type, exc, tb)

    def thread_hook(args: threading.ExceptHookArgs) -> None:
        exc = args.exc_value
        message = (
            str(exc) if exc is not None else (args.exc_type.__name__ if args.exc_type else "Error")
        )
        stack = ""
        if args.exc_type is not None and exc is not None:
            stack = "".join(traceback.format_exception(args.exc_type, exc, args.exc_traceback))
        store(message, stack)
        if _prev_thread is not None:
            _prev_thread(args)

    sys.excepthook = hook
    threading.excepthook = thread_hook


def reset_install_for_tests() -> None:
    """Restore hooks after tests that call install_crash_handler."""
    global _installed, _prev_hook, _prev_thread
    if _prev_hook is not None:
        sys.excepthook = _prev_hook
    if _prev_thread is not None:
        threading.excepthook = _prev_thread
    _installed = False
    _prev_hook = None
    _prev_thread = None
