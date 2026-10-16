"""Bots hub: live status, plan builder, performance, FAB for manual create."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QVBoxLayout, QWidget

from trendalgo.device import strings as S
from trendalgo.device.bots_performance import performance_rows
from trendalgo.device.context import DeviceContext
from trendalgo.device.stores import StoreReadError
from trendalgo.device.views.plan_page import PlanPage
from trendalgo.device.views.status_page import StatusPage
from trendalgo.device.views.widgets import (
    EmptyState,
    fill_table,
    mark_primary,
    page_header,
    read_only_table,
    section_title,
    tint_signed,
)


class BotsPage(QWidget):
    def __init__(
        self,
        ctx: DeviceContext,
        *,
        on_host_badge: Callable[..., None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._ctx = ctx
        self._builder = PlanPage(ctx)
        self._builder.setObjectName("botsBuilder")
        self._hide_nested_header(self._builder)
        self._status = StatusPage(
            ctx,
            on_build_plan=self.focus_manual_create,
            on_host_badge=on_host_badge,
        )
        self._hide_nested_header(self._status)
        self._perf = read_only_table(S.BOTS_PERF_HEADERS, S.BOTS_PERF_TITLE)
        self._perf_empty = EmptyState(S.BOTS_PERF_EMPTY_TITLE, S.BOTS_PERF_EMPTY_BODY)
        self._fab = mark_primary(QPushButton(S.BOTS_FAB_ADD))
        self._fab.clicked.connect(lambda _c=False: self.focus_manual_create())
        self._fab.setAccessibleName(S.BOTS_FAB_ADD)

        layout = QVBoxLayout(self)
        layout.addWidget(page_header(S.STATUS_TITLE, S.STATUS_SUBTITLE))
        layout.addWidget(self._status)
        layout.addWidget(section_title(S.BOTS_PERF_TITLE))
        layout.addWidget(self._perf_empty)
        layout.addWidget(self._perf)
        layout.addWidget(section_title(S.BOTS_BUILDER_TITLE))
        layout.addWidget(self._builder)
        fab_row = QHBoxLayout()
        fab_row.addStretch(1)
        fab_row.addWidget(self._fab, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addLayout(fab_row)
        self.reload_performance()

    @staticmethod
    def _hide_nested_header(page: QWidget) -> None:
        layout = page.layout()
        if layout is None or layout.count() < 1:
            return
        item = layout.itemAt(0)
        if item is None:
            return
        header = item.widget()
        if header is not None:
            header.hide()

    def focus_manual_create(self) -> None:
        self._builder.prefill_from_fleet(
            {
                "name": "",
                "pair": "",
                "timeframe": "1h",
                "indicator": "",
                "stake": "100",
                "stop": "5",
            }
        )
        self._builder._name.setFocus()  # noqa: SLF001 — form focus for FAB

    def prefill_from_fleet(self, fields: dict[str, str]) -> None:
        self._builder.prefill_from_fleet(fields)

    def add_bot_from_fields(self, fields: dict[str, str]) -> tuple[bool, str]:
        return self._builder.add_bot_from_fields(fields)

    def reload_performance(self) -> None:
        try:
            rows = performance_rows(self._ctx.databases["bots"], self._ctx.databases["journal"])
        except StoreReadError:
            rows = []
        fill_table(
            self._perf,
            [
                (
                    r.display_label,
                    r.pair,
                    r.strategy,
                    str(r.trade_count),
                    f"{r.win_rate:.0%}" if r.win_rate is not None else "—",
                    f"${r.realized_pnl:+,.2f}",
                )
                for r in rows
            ],
        )
        for index, row in enumerate(rows):
            item = self._perf.item(index, 5)
            if item is not None:
                tint_signed(item, row.realized_pnl)
        self._perf.setVisible(bool(rows))
        self._perf_empty.setVisible(not rows)

    def reload(self) -> None:
        self._status.reload()
        self.reload_performance()
