"""Reusable chevron collapsible section for Settings and nested categories."""

from __future__ import annotations

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

_CHEVRON_COLLAPSED = "▶"
_CHEVRON_EXPANDED = "▼"


class CollapsibleSection(QWidget):
    toggled = Signal(bool)

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
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        self._chevron = QLabel(_CHEVRON_EXPANDED if expanded else _CHEVRON_COLLAPSED)
        self._chevron.setObjectName("collapseChevron")
        self._chevron.setFixedWidth(22)
        self._chevron.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title = QLabel(title)
        self._title.setObjectName("sectionTitle" if not nested else "hint")
        self._body = QWidget()
        self._body.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        self._body_layout = QVBoxLayout(self._body)
        self._body_layout.setContentsMargins(12 if nested else 4, 6, 0, 6)
        self._body_layout.setSpacing(8)
        self._body.setVisible(expanded)

        self._header = QFrame()
        self._header.setObjectName("collapseHeader")
        self._header.setCursor(Qt.CursorShape.PointingHandCursor)
        head = QHBoxLayout(self._header)
        head.setContentsMargins(2, 4, 2, 4)
        head.setSpacing(6)
        head.addWidget(self._chevron)
        head.addWidget(self._title, 1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
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
        changed = bool(expanded) != self._expanded
        self._expanded = bool(expanded)
        self._body.setVisible(self._expanded)
        self._chevron.setText(_CHEVRON_EXPANDED if self._expanded else _CHEVRON_COLLAPSED)
        self._body.updateGeometry()
        self.updateGeometry()
        if changed:
            self.toggled.emit(self._expanded)

    def _flip(self) -> None:
        self.set_expanded(not self._expanded)
