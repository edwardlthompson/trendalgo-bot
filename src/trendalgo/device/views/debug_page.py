"""Debug log viewer: last lines from the profile device.log file."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget

from trendalgo.device import strings as S
from trendalgo.device.context import DeviceContext
from trendalgo.device.debug_log_model import DEFAULT_TAIL_LINES, tail_device_log
from trendalgo.device.views.widgets import EmptyState, TailFill, page_header


class DebugPage(QWidget):
    def __init__(self, ctx: DeviceContext, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._ctx = ctx
        self._count = QLabel()
        self._count.setObjectName("hint")
        self._empty = EmptyState(S.DEBUG_EMPTY_TITLE, S.DEBUG_EMPTY_BODY)
        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setPlaceholderText(S.DEBUG_PLACEHOLDER)
        self._reload = QPushButton(S.DEBUG_REFRESH)
        self._reload.clicked.connect(lambda _checked=False: self.refresh())
        layout = QVBoxLayout(self)
        layout.addWidget(page_header(S.DEBUG_TITLE, S.DEBUG_SUBTITLE))
        layout.addWidget(self._reload, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self._count)
        layout.addWidget(self._empty)
        layout.addWidget(self._log)
        self._fill = TailFill(layout, self._log)
        self.refresh()

    def refresh(self) -> None:
        lines = tail_device_log(self._ctx.root)
        has_lines = bool(lines)
        self._log.setPlainText("\n".join(lines))
        self._log.setVisible(has_lines)
        self._empty.setVisible(not has_lines)
        if has_lines:
            self._count.setText(S.DEBUG_LINE_COUNT.format(n=len(lines), max=DEFAULT_TAIL_LINES))
        else:
            self._count.clear()
        self._fill.update(has_lines)
