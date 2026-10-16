"""Shared Qt pieces: page header, labeled field, problem text, empty state, and a read-only table."""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QBoxLayout,
    QFrame,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from trendalgo.device import strings as S
from trendalgo.device.theme import active_mode
from trendalgo.device.theme_css import colors_for


def page_header(title: str, subtitle: str) -> QWidget:
    box = QWidget()
    layout = QVBoxLayout(box)
    layout.setContentsMargins(0, 0, 0, 0)
    heading = QLabel(title)
    heading.setObjectName("pageTitle")
    note = QLabel(subtitle)
    note.setObjectName("subtitle")
    note.setWordWrap(True)
    layout.addWidget(heading)
    layout.addWidget(note)
    return box


def field(label_text: str, editor: QWidget, help_text: str = "") -> QWidget:
    """Label above the editor, helper text under it. The label is also the accessible name."""
    box = QWidget()
    layout = QVBoxLayout(box)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(QLabel(label_text))
    layout.addWidget(editor)
    editor.setAccessibleName(label_text)
    if help_text:
        editor.setAccessibleDescription(help_text)
        hint = QLabel(help_text)
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        layout.addWidget(hint)
    return box


class TailFill:
    """Hands spare window height to one primary widget (table, log, …), else a blank tail.

    Without a stretch item, Qt spreads spare height over every label, which opens gaps between the
    title, the subtitle, and the content. Call `update` whenever the target is shown or hidden.
    """

    def __init__(self, layout: QBoxLayout, table: QWidget) -> None:
        self._layout = layout
        self._target = table
        layout.addStretch(1)
        self._tail = layout.count() - 1

    def set_target(self, widget: QWidget) -> None:
        if widget is self._target:
            return
        self._layout.setStretchFactor(self._target, 0)
        self._target = widget

    def update(self, shown: bool) -> None:
        self._layout.setStretchFactor(self._target, 1 if shown else 0)
        self._layout.setStretch(self._tail, 0 if shown else 1)


def mark_primary(button: QPushButton) -> QPushButton:
    """Mark the one action a view is for. The stylesheet gives it the emphasis."""
    button.setProperty("role", "primary")
    return button


def section_title(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("sectionTitle")
    return label


def problem_label() -> QLabel:
    label = QLabel()
    label.setObjectName("problem")
    label.setWordWrap(True)
    label.hide()
    return label


def show_problem(label: QLabel, message: str) -> None:
    """Say what went wrong in plain text (the prefix keeps it readable without color)."""
    label.setText(f"{S.PROBLEM_PREFIX}{message}")
    label.show()


def clear_problem(label: QLabel) -> None:
    label.clear()
    label.hide()


class EmptyState(QFrame):
    """Why a view is empty, plus at most one button that fixes it."""

    def __init__(
        self,
        title: str,
        body: str,
        action: str = "",
        on_action: Callable[[], None] | None = None,
    ) -> None:
        super().__init__()
        self.setObjectName("emptyState")
        layout = QVBoxLayout(self)
        self._title = QLabel(title)
        self._title.setObjectName("emptyTitle")
        self._title.setWordWrap(True)
        self._body = QLabel(body)
        self._body.setWordWrap(True)
        layout.addWidget(self._title)
        layout.addWidget(self._body)
        self.button = QPushButton(action)
        self.button.setVisible(bool(action) and on_action is not None)
        if on_action is not None:
            self.button.clicked.connect(lambda _checked=False: on_action())
        layout.addWidget(self.button, alignment=Qt.AlignmentFlag.AlignLeft)

    def set_text(self, title: str, body: str) -> None:
        self._title.setText(title)
        self._body.setText(body)


def read_only_table(headers: Sequence[str], name: str) -> QTableWidget:
    table = QTableWidget(0, len(headers))
    table.setHorizontalHeaderLabels(list(headers))
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    table.verticalHeader().setVisible(False)
    table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    table.setAlternatingRowColors(True)
    table.setAccessibleName(name)
    return table


def fill_table(table: QTableWidget, rows: Sequence[Sequence[str]]) -> None:
    table.setRowCount(len(rows))
    for row_index, values in enumerate(rows):
        for column, value in enumerate(values):
            table.setItem(row_index, column, QTableWidgetItem(value))


def tint_signed(item: QTableWidgetItem, value: float) -> None:
    """Profit uses the secondary token; loss uses error. Zero stays the default text color."""
    if value == 0 or not math.isfinite(value):
        return
    colors = colors_for(active_mode())
    key = "secondary" if value > 0 else "error"
    item.setForeground(QColor(colors[key]))
