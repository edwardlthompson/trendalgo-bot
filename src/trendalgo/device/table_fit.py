"""Size QTableWidget columns so cell text is not cropped."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHeaderView, QTableWidget


def fit_table_columns(table: QTableWidget) -> None:
    """Resize every column to its contents and allow horizontal scroll if needed."""
    header = table.horizontalHeader()
    header.setStretchLastSection(False)
    header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    table.resizeColumnsToContents()
    table.resizeRowsToContents()
    # Lock measured widths so Stretch from read_only_table cannot shrink them again.
    for col in range(table.columnCount()):
        width = max(table.columnWidth(col), table.sizeHintForColumn(col))
        header.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)
        table.setColumnWidth(col, width)
