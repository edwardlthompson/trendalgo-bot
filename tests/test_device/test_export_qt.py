"""Headless export Qt: pin fonts under empty offscreen font DB + dark theme."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtGui import QFontDatabase  # noqa: E402
from PySide6.QtWidgets import QApplication, QLabel  # noqa: E402

from trendalgo.device.export_qt import ensure_export_qapp, pin_export_fonts  # noqa: E402
from trendalgo.device.theme import active_mode  # noqa: E402


def test_ensure_export_qapp_dark_and_fonts(tmp_path) -> None:
    # Fresh process may already have a QApplication from other tests — still pin + dark.
    app = ensure_export_qapp(tmp_path, force_dark=True)
    assert isinstance(app, QApplication)
    assert active_mode() == "dark"
    pin_export_fonts()
    assert QFontDatabase.families(), "expected system fonts registered for offscreen grab"
    lab = QLabel("AUD/JPY")
    lab.adjustSize()
    pix = lab.grab()
    out = tmp_path / "label.png"
    assert pix.save(str(out), "PNG")
    assert out.stat().st_size > 200
