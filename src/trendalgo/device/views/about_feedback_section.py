"""About feedback: one dropdown + Open (Report a bug / Request a feature)."""

from __future__ import annotations

from typing import cast

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QLabel, QPushButton, QVBoxLayout, QWidget

from trendalgo.device.context import DeviceContext
from trendalgo.device.feedback import copy as C
from trendalgo.device.views.feedback_dialog import FeedbackKind, open_feedback
from trendalgo.device.views.widgets import field


class AboutFeedbackSection(QWidget):
    def __init__(self, ctx: DeviceContext, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._ctx = ctx
        self._kind = QComboBox()
        self._kind.addItem(C.BUG_TITLE, "bug")
        self._kind.addItem(C.FEATURE_TITLE, "feature")
        self._kind.setAccessibleName("Feedback")
        self._kind.setMaximumWidth(520)
        open_btn = QPushButton("Open")
        open_btn.setMinimumHeight(44)
        open_btn.clicked.connect(lambda _c=False: self._open())
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(field("Feedback", self._kind))
        layout.addWidget(open_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        hint = QLabel(C.CLIPBOARD_HINT)
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        layout.addWidget(hint)

    def _open(self) -> None:
        kind = cast(FeedbackKind, str(self._kind.currentData() or "bug"))
        open_feedback(self._ctx, kind, parent=self.window())
