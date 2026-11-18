"""Success-only Backtest completion: beep + tray toast + dialog if active."""

from __future__ import annotations

import os
from typing import Any

from PySide6.QtWidgets import QApplication, QMessageBox, QWidget

from trendalgo.device.backtest_notify import notify_body, notify_title


def announce_backtest_done(page: QWidget, *, elapsed_s: float | None = None) -> None:
    """Beep always; toast via on_toast; modal only when the window is active."""
    try:
        QApplication.beep()
    except Exception:
        pass
    title = notify_title()
    body = notify_body(elapsed_s=elapsed_s)
    on_toast = getattr(page, "_on_toast", None)
    if callable(on_toast):
        try:
            on_toast(title, body)
        except Exception:
            pass
    # Unit tests: never block on a modal.
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return
    win = page.window() if isinstance(page, QWidget) else None
    active = False
    if isinstance(win, QWidget):
        try:
            active = bool(win.isActiveWindow())
        except Exception:
            active = False
    if active:
        QMessageBox.information(page, title, body)


def unpack_job_meta(payload: object) -> dict[str, Any]:
    """Pull elapsed / source fields from the worker payload."""
    if not isinstance(payload, dict):
        return {}
    out: dict[str, Any] = {}
    if "elapsed_s" in payload:
        try:
            out["elapsed_s"] = float(payload["elapsed_s"])
        except (TypeError, ValueError):
            pass
    if payload.get("data_source"):
        out["data_source"] = str(payload["data_source"])
    if payload.get("cache_age_s") is not None:
        try:
            out["cache_age_s"] = float(payload["cache_age_s"])
        except (TypeError, ValueError):
            pass
    return out
