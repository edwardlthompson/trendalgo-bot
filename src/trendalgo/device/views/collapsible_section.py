"""Reusable chevron collapsible section for Settings and nested categories."""

from __future__ import annotations

from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

_CHEVRON_COLLAPSED = "▶"
_CHEVRON_EXPANDED = "▼"


class CollapsibleSection(QWidget):
    def __init__(
        self,
        title: str,
        *,
        expanded: bool = True,
        nested: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._expanded = expanded
        self._chevron = QLabel(_CHEVRON_EXPANDED if expanded else _CHEVRON_COLLAPSED)
        self._chevron.setObjectName("collapseChevron")
        self._chevron.setFixedWidth(22)
        self._chevron.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title = QLabel(title)
        self._title.setObjectName("sectionTitle" if not nested else "hint")
        self._body = QWidget()
        self._body_layout = QVBoxLayout(self._body)
        self._body_layout.setContentsMargins(18 if nested else 8, 4, 0, 4)
        self._body_layout.setSpacing(6)
        self._body.setVisible(expanded)

        self._header = QFrame()
        self._header.setObjectName("collapseHeader")
        self._header.setCursor(Qt.CursorShape.PointingHandCursor)
        head = QHBoxLayout(self._header)
        head.setContentsMargins(0, 4, 0, 4)
        head.setSpacing(6)
        head.addWidget(self._chevron)
        head.addWidget(self._title, 1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(2)
        layout.addWidget(self._header)
        layout.addWidget(self._body)
        self._header.installEventFilter(self)

    def eventFilter(self, watched: object, event: QEvent) -> bool:  # noqa: N802
        if watched is self._header and event.type() == QEvent.Type.MouseButtonPress:
            self._flip()
            return True
        return super().eventFilter(watched, event)

    def body_layout(self) -> QVBoxLayout:
        return self._body_layout

    def add_widget(self, widget: QWidget) -> None:
        self._body_layout.addWidget(widget)

    def set_expanded(self, expanded: bool) -> None:
        self._expanded = expanded
        self._body.setVisible(expanded)
        self._chevron.setText(_CHEVRON_EXPANDED if expanded else _CHEVRON_COLLAPSED)

    def _flip(self) -> None:
        self.set_expanded(not self._expanded)
