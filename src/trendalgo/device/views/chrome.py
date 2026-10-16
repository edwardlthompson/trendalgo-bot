"""Header above the sections: brand mark, name, status text, and the host badge."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from trendalgo.device import strings as S
from trendalgo.device.icons import brand_mark

MARK_PX = 28


class BrandHeader(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        mark = QLabel()
        mark.setPixmap(brand_mark(MARK_PX))
        name = QLabel(S.APP_TITLE)
        name.setObjectName("brandName")
        status = QLabel(S.HEADER_STATUS)
        status.setObjectName("status")
        self.badge = QLabel(S.BADGE_NO_HOST)
        self.badge.setObjectName("badge")
        self.badge.setAccessibleName(S.BADGE_NO_HOST)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(12)
        row.addWidget(mark)
        row.addWidget(name)
        row.addWidget(status)
        row.addStretch(1)
        row.addWidget(self.badge, alignment=Qt.AlignmentFlag.AlignVCenter)

    def set_host_link(self, linked: bool, *, pending_events: int = 0) -> None:
        if not linked:
            text = S.BADGE_NO_HOST
        elif pending_events > 0:
            text = S.BADGE_HOST_EVENTS.format(count=pending_events)
        else:
            text = S.BADGE_HOST_LINKED
        self.badge.setText(text)
        self.badge.setAccessibleName(text)
