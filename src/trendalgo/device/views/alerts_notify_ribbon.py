"""Alerts page ribbon: kind master toggles, preview, Test Windows / Telegram."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from trendalgo.device import strings as S
from trendalgo.device.alert_preview import (
    KINDS,
    kind_master_on,
    sample_event,
    set_kind_master,
    telegram_preview,
    windows_preview,
)
from trendalgo.device.notify_prefs import load_prefs, save_prefs
from trendalgo.device.telegram_vault import load_telegram_creds
from trendalgo.device.views.widgets import clear_problem, problem_label, show_problem
from trendalgo.notifications.telegram import TelegramCommands
from trendalgo.notifications.telegram_chart import chart_png_bytes, closes_from_coin

_KIND_LABEL = {
    "entered": S.ALERTS_TAB_ENTERED,
    "left": S.ALERTS_TAB_LEFT,
    "trades": S.ALERTS_TAB_TRADES,
}


class AlertsNotifyRibbon(QWidget):
    def __init__(
        self,
        root: Path,
        *,
        on_toast: Callable[[str, str], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._root = root
        self._on_toast = on_toast
        self._kind = "entered"
        self._toggles: dict[str, QToolButton] = {}
        self._syncing = False
        help_lbl = QLabel(S.ALERTS_RIBBON_HELP)
        help_lbl.setObjectName("hint")
        help_lbl.setWordWrap(True)
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        for kind in KINDS:
            btn = QToolButton()
            btn.setCheckable(True)
            btn.setObjectName(f"alertsNotify_{kind}")
            btn.setAccessibleName(_KIND_LABEL[kind])
            self._toggles[kind] = btn
            btn.clicked.connect(lambda checked=False, k=kind: self._on_toggle(k, bool(checked)))
            row.addWidget(btn)
        row.addStretch(1)
        self._win_title = QLabel()
        self._win_body = QLabel()
        self._win_body.setWordWrap(True)
        self._win_body.setObjectName("hint")
        self._tg_body = QLabel()
        self._tg_body.setWordWrap(True)
        self._tg_body.setObjectName("hint")
        self._tg_body.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._status = QLabel()
        self._status.setWordWrap(True)
        self._problem = problem_label()
        test_win = QPushButton(S.ALERTS_TEST_WINDOWS)
        test_win.clicked.connect(lambda _c=False: self._test_windows())
        test_tg = QPushButton(S.ALERTS_TEST_TELEGRAM)
        test_tg.clicked.connect(lambda _c=False: self._test_telegram())
        tests = QHBoxLayout()
        tests.setContentsMargins(0, 0, 0, 0)
        tests.addWidget(test_win)
        tests.addWidget(test_tg)
        tests.addStretch(1)
        win_head = QLabel(S.ALERTS_PREVIEW_WINDOWS)
        win_head.setObjectName("subtitle")
        tg_head = QLabel(S.ALERTS_PREVIEW_TELEGRAM)
        tg_head.setObjectName("subtitle")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 8)
        layout.setSpacing(6)
        layout.addWidget(help_lbl)
        layout.addLayout(row)
        layout.addWidget(win_head)
        layout.addWidget(self._win_title)
        layout.addWidget(self._win_body)
        layout.addWidget(tg_head)
        layout.addWidget(self._tg_body)
        layout.addLayout(tests)
        layout.addWidget(self._problem)
        layout.addWidget(self._status)
        self.reload()

    def reload(self) -> None:
        prefs = load_prefs(self._root)
        self._syncing = True
        try:
            for kind, btn in self._toggles.items():
                on = kind_master_on(prefs, kind)
                state = S.ALERTS_NOTIFY_ON if on else S.ALERTS_NOTIFY_OFF
                btn.setText(f"{_KIND_LABEL[kind]} · {state}")
                btn.setChecked(on)
        finally:
            self._syncing = False
        self._refresh_preview()

    def set_kind(self, kind: str) -> None:
        if kind not in KINDS:
            return
        self._kind = kind
        self._refresh_preview()

    def _on_toggle(self, kind: str, enabled: bool) -> None:
        if self._syncing:
            return
        self._kind = kind
        prefs = load_prefs(self._root)
        save_prefs(self._root, set_kind_master(prefs, kind, enabled))
        self.reload()

    def _refresh_preview(self) -> None:
        event = sample_event(self._kind)
        title, body = windows_preview(event)
        self._win_title.setText(title)
        self._win_body.setText(body)
        self._tg_body.setText(telegram_preview(event))

    def _test_windows(self) -> None:
        clear_problem(self._problem)
        title, body = windows_preview(sample_event(self._kind))
        if self._on_toast is not None:
            self._on_toast(title, body)
            self._status.setText(S.ALERTS_TEST_OK)
            return
        self._status.setText(f"{title}\n{body}")

    def _test_telegram(self) -> None:
        clear_problem(self._problem)
        token, chat = load_telegram_creds()
        if not token or not chat:
            show_problem(self._problem, S.ALERTS_TEST_TG_NEED)
            return
        prefs = load_prefs(self._root)
        if not prefs.telegram_enabled:
            show_problem(self._problem, S.ALERTS_TEST_TG_NEED)
            return
        tg = TelegramCommands(token=token, chat_id=chat)
        event = sample_event(self._kind)
        text = telegram_preview(event)
        ok = False
        if event.kind == "qualified_enter" and event.coin is not None:
            png = chart_png_bytes(closes_from_coin(event.coin), title=event.symbol)
            ok = tg.send_photo(png, text) if png else tg.send_message(text)
        else:
            ok = tg.send_message(text)
        if ok:
            self._status.setText(S.ALERTS_TEST_OK)
        else:
            show_problem(self._problem, S.ALERTS_TEST_TG_FAIL)
