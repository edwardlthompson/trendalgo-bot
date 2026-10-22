"""Labeled read-only snippet with a Copy button for clipboard paste."""

from __future__ import annotations

from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from trendalgo.device import strings as S


class CopySnippet(QWidget):
    def __init__(self, label: str, text: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._text = text
        self._field = QLineEdit(text)
        self._field.setReadOnly(True)
        mono = QFont(self._field.font())
        mono.setStyleHint(QFont.StyleHint.Monospace)
        mono.setFamily("Consolas")
        self._field.setFont(mono)
        self._field.setAccessibleName(label)
        copy = QPushButton(S.TG_WIZARD_COPY)
        copy.setAccessibleName(f"{S.TG_WIZARD_COPY} {label}")
        copy.clicked.connect(lambda _c=False: self.copy())
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self._field, stretch=1)
        row.addWidget(copy)
        box = QVBoxLayout(self)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(4)
        box.addWidget(QLabel(label))
        box.addLayout(row)

    def text(self) -> str:
        return self._text

    def set_text(self, text: str) -> None:
        self._text = text
        self._field.setText(text)

    def copy(self) -> bool:
        app = QApplication.instance()
        if not isinstance(app, QApplication):
            return False
        clip = app.clipboard()
        if clip is None:
            return False
        clip.setText(self._text)
        return True
