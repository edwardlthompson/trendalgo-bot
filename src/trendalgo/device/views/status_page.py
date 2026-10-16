"""Bot status and journal: local store plus optional host poll and controls."""

from __future__ import annotations

import secrets
from collections.abc import Callable

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from trendalgo.device import strings as S
from trendalgo.device.context import DeviceContext
from trendalgo.device.host_actions import host_health_linked, post_bot_command
from trendalgo.device.host_client import UNREACHABLE, HostRefusedError
from trendalgo.device.host_session import try_open_host_client
from trendalgo.device.rows import BotRow, bot_rows, trade_rows
from trendalgo.device.stores import StoreReadError, read_bots, read_trades
from trendalgo.device.views.bot_cards import BotCardList
from trendalgo.device.views.widgets import (
    EmptyState,
    TailFill,
    clear_problem,
    fill_table,
    page_header,
    problem_label,
    read_only_table,
    section_title,
    show_problem,
    tint_signed,
)
from trendalgo.device.wizard.credentials import CredentialStore


class StatusPage(QWidget):
    def __init__(
        self,
        ctx: DeviceContext,
        on_build_plan: Callable[[], None],
        *,
        on_host_badge: Callable[..., None] | None = None,
        credential_store: CredentialStore | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._ctx = ctx
        self._on_host_badge = on_host_badge
        self._vault = credential_store
        self._bots: list[BotRow] = []
        self._problem = problem_label()
        self._host_status = QLabel()
        self._host_status.setObjectName("hint")
        self._host_status.setWordWrap(True)
        self._reload = QPushButton(S.RELOAD)
        self._reload.clicked.connect(lambda _checked=False: self.reload())
        self._bots_empty = EmptyState(
            S.STATUS_BOTS_EMPTY_TITLE,
            S.STATUS_BOTS_EMPTY_BODY,
            S.STATUS_GO_PLAN,
            on_build_plan,
        )
        self._cards = BotCardList()
        self._journal_empty = EmptyState(S.STATUS_JOURNAL_EMPTY_TITLE, S.STATUS_JOURNAL_EMPTY_BODY)
        self._journal = read_only_table(S.STATUS_JOURNAL_HEADERS, S.STATUS_JOURNAL)
        layout = QVBoxLayout(self)
        layout.addWidget(page_header(S.STATUS_TITLE, S.STATUS_SUBTITLE))
        layout.addWidget(self._reload, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self._problem)
        layout.addWidget(self._host_status)
        layout.addWidget(section_title(S.STATUS_BOTS))
        layout.addWidget(self._bots_empty)
        layout.addWidget(self._cards)
        layout.addWidget(section_title(S.STATUS_JOURNAL))
        layout.addWidget(self._journal_empty)
        layout.addWidget(self._journal)
        self._fill = TailFill(layout, self._journal)
        self._timer = QTimer(self)
        self._timer.setInterval(15_000)
        self._timer.timeout.connect(self._poll_host)
        self._timer.start()
        self.reload()

    def reload(self) -> None:
        try:
            self._bots = bot_rows(read_bots(self._ctx.databases["bots"]))
            trades = trade_rows(read_trades(self._ctx.databases["journal"]))
        except StoreReadError as exc:
            show_problem(self._problem, str(exc))
            return
        clear_problem(self._problem)
        self._bots_empty.setVisible(not self._bots)
        fill_table(self._journal, [(t.time, t.pair, t.side, t.pnl, t.source) for t in trades])
        for index, trade in enumerate(trades):
            item = self._journal.item(index, 3)
            if item is not None:
                tint_signed(item, trade.pnl_value)
        self._journal.setVisible(bool(trades))
        self._fill.update(bool(trades))
        self._journal_empty.setVisible(not trades)
        self._poll_host()

    def _poll_host(self) -> None:
        client = try_open_host_client(self._ctx.settings_path, store=self._vault)
        if client is None:
            self._host_status.clear()
            self._apply_host_controls(False)
            self._update_badge(False, 0)
            return
        try:
            status = client.get_status()
        except HostRefusedError:
            self._host_status.setText(S.STATUS_HOST_OFFLINE)
            self._apply_host_controls(False)
            self._update_badge(False, 0)
            return
        linked = host_health_linked(status)
        pending = int((status.data or {}).get("pending_events", 0)) if linked else 0
        if linked:
            version = int((status.data or {}).get("plan_version", 0))
            self._host_status.setText(S.STATUS_HOST_POLL.format(version=version, events=pending))
        elif status.status == UNREACHABLE:
            self._host_status.setText(S.STATUS_HOST_OFFLINE)
        else:
            self._host_status.setText(S.STATUS_HOST_OFFLINE)
        self._apply_host_controls(linked)
        self._update_badge(linked, pending)

    def _apply_host_controls(self, linked: bool) -> None:
        self._cards.set_host_controls(linked, on_command=self._post_command if linked else None)
        self._cards.set_bots(self._bots)
        self._cards.setVisible(bool(self._bots))

    def _update_badge(self, linked: bool, pending: int) -> None:
        if self._on_host_badge is not None:
            self._on_host_badge(linked, pending_events=pending)

    def _post_command(self, action: str, bot_id: str) -> None:
        client = try_open_host_client(self._ctx.settings_path, store=self._vault)
        if client is None:
            show_problem(self._problem, S.PLAN_SEND_NO_HOST)
            return
        key = secrets.token_urlsafe(12)
        try:
            response = post_bot_command(client, action, bot_id, key)
        except HostRefusedError as exc:
            show_problem(self._problem, exc.problem.message)
            return
        if not response.ok:
            show_problem(self._problem, S.STATUS_ACTION_FAILED)
            return
        clear_problem(self._problem)
        self._poll_host()
