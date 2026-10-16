"""Collapsible activity log: full scroll, or one-line latest when collapsed."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

_LINE_PX = 28
_EXPANDED_PX = 140


class CollapsibleLog(QWidget):
    def __init__(self, title: str, *, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._expanded = False
        self._last = ""
        self._toggle = QPushButton("▸")
        self._toggle.setFixedWidth(28)
        self._toggle.setToolTip("Expand or collapse activity")
        self._toggle.clicked.connect(lambda _c=False: self._flip())
        self._title = QLabel(title)
        self._title.setObjectName("sectionTitle")
        self._one = QLabel("—")
        self._one.setObjectName("hint")
        self._one.setWordWrap(False)
        self._one.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setMaximumBlockCount(500)
        self._log.setPlaceholderText(title)
        self._log.hide()

        head = QHBoxLayout()
        head.setContentsMargins(0, 0, 0, 0)
        head.addWidget(self._toggle)
        head.addWidget(self._title, 1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addLayout(head)
        layout.addWidget(self._one)
        layout.addWidget(self._log)
        self._apply_height()

    def clear(self) -> None:
        self._log.clear()
        self._last = ""
        self._one.setText("—")

    def append(self, line: str) -> None:
        text = str(line or "").strip()
        if not text:
            return
        self._last = text
        self._log.appendPlainText(text)
        self._one.setText(text)

    def _flip(self) -> None:
        self._expanded = not self._expanded
        self._toggle.setText("▾" if self._expanded else "▸")
        self._log.setVisible(self._expanded)
        self._one.setVisible(not self._expanded)
        self._apply_height()

    def _apply_height(self) -> None:
        if self._expanded:
            self._log.setMinimumHeight(_EXPANDED_PX)
            self._log.setMaximumHeight(16777215)
            self.setMaximumHeight(16777215)
        else:
            self._log.setMinimumHeight(0)
            self._log.setMaximumHeight(0)
            self._one.setFixedHeight(_LINE_PX)
            self.setMaximumHeight(_LINE_PX + 36)
