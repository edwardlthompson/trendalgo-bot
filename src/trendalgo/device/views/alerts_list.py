"""Alerts tab: history table for scan enter/leave events."""

from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from trendalgo.device import strings as S
from trendalgo.device.views.widgets import EmptyState, read_only_table


class AlertsList(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._empty = EmptyState(S.SCANNER_ALERTS_EMPTY_TITLE, S.SCANNER_ALERTS_EMPTY_BODY)
        self._table = read_only_table(S.SCANNER_ALERTS_HEADERS, S.SCANNER_TAB_ALERTS)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._empty)
        layout.addWidget(self._table)
        self.set_rows([])

    def set_rows(self, rows: list[dict[str, Any]]) -> None:
        has = bool(rows)
        self._empty.setVisible(not has)
        self._table.setVisible(has)
        if not has:
            self._table.setRowCount(0)
            return
        self._table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            kind = str(row.get("kind") or "")
            label = {
                "qualified_enter": "Entered",
                "watchlist_leave": "Left",
                "trade_alert": "Trade",
                "scan_log": "Scan log",
                "backtest_log": "Backtest log",
            }.get(kind, kind)
            values = (
                str(row.get("at") or "")[:19],
                label,
                str(row.get("symbol") or row.get("pair") or ""),
                str(row.get("reason") or ""),
            )
            for c, text in enumerate(values):
                self._table.setItem(r, c, QTableWidgetItem(text))
        self._table.resizeColumnsToContents()


def as_table_widget(widget: AlertsList) -> QTableWidget:
    return widget._table  # noqa: SLF001 — test helper
