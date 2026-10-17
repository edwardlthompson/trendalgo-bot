"""Settings section: opt-in save-crashes toggle."""

from __future__ import annotations

from PySide6.QtWidgets import QCheckBox, QLabel, QVBoxLayout, QWidget

from trendalgo.device.context import DeviceContext
from trendalgo.device.crash_capture import copy as C
from trendalgo.device.crash_capture.pending_crash import on_save_crashes_changed
from trendalgo.device.crash_capture.save_crashes import get_save_crashes, set_save_crashes
from trendalgo.device.views.widgets import section_title


class CrashPrivacySection(QWidget):
    def __init__(self, ctx: DeviceContext, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._ctx = ctx
        self._box = QCheckBox(C.SAVE_CRASHES)
        help_lbl = QLabel(C.SAVE_CRASHES_HELP)
        help_lbl.setObjectName("hint")
        help_lbl.setWordWrap(True)
        self._box.toggled.connect(self._on_toggled)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(section_title(C.PRIVACY_SECTION))
        layout.addWidget(self._box)
        layout.addWidget(help_lbl)
        self._box.setChecked(get_save_crashes(ctx.root))

    def _on_toggled(self, checked: bool) -> None:
        set_save_crashes(self._ctx.root, checked)
        on_save_crashes_changed(self._ctx.root, checked)
