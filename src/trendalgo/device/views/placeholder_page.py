"""Placeholder page for More-menu sections until their parity row lands."""

from __future__ import annotations

from PySide6.QtWidgets import QVBoxLayout, QWidget

from trendalgo.device.views.widgets import EmptyState, page_header


class PlaceholderPage(QWidget):
    def __init__(self, title: str, subtitle: str, empty_title: str, empty_body: str) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(page_header(title, subtitle))
        layout.addWidget(EmptyState(empty_title, empty_body), 1)
