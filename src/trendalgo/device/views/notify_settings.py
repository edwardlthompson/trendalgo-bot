"""Settings section: Windows × Telegram toggles per alert kind."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QGridLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from trendalgo.device import strings as S
from trendalgo.device.autostart import set_enabled as set_autostart
from trendalgo.device.context import DeviceContext
from trendalgo.device.host_session import try_open_host_client
from trendalgo.device.notify_prefs import NotifyPrefs, load_prefs, save_prefs
from trendalgo.device.telegram_vault import load_telegram_creds
from trendalgo.device.views.widgets import mark_primary


class NotifySettingsSection(QWidget):
    def __init__(
        self,
        ctx: DeviceContext,
        *,
        on_saved: Callable[[], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._ctx = ctx
        self._on_saved = on_saved
        self._tg = QCheckBox(S.NOTIFY_TELEGRAM)
        self._autostart = QCheckBox(S.NOTIFY_START_WINDOWS)
        self._status = QLabel()
        self._win: dict[str, QCheckBox] = {}
        self._tg_kind: dict[str, QCheckBox] = {}
        grid = QGridLayout()
        grid.addWidget(QLabel(""), 0, 0)
        grid.addWidget(QLabel(S.NOTIFY_COL_WINDOWS), 0, 1)
        grid.addWidget(QLabel(S.NOTIFY_COL_TELEGRAM), 0, 2)
        rows = (
            ("logs", S.NOTIFY_KIND_LOGS),
            ("entered", S.NOTIFY_KIND_ENTERED),
            ("left", S.NOTIFY_KIND_LEFT),
            ("trades", S.NOTIFY_KIND_TRADES),
        )
        for i, (key, title) in enumerate(rows, start=1):
            grid.addWidget(QLabel(title), i, 0)
            w = QCheckBox()
            t = QCheckBox()
            self._win[key] = w
            self._tg_kind[key] = t
            grid.addWidget(w, i, 1, alignment=Qt.AlignmentFlag.AlignCenter)
            grid.addWidget(t, i, 2, alignment=Qt.AlignmentFlag.AlignCenter)
        help_lbl = QLabel(S.NOTIFY_SECTION_HELP)
        help_lbl.setObjectName("hint")
        help_lbl.setWordWrap(True)
        auto_help = QLabel(S.NOTIFY_START_WINDOWS_HELP)
        auto_help.setObjectName("hint")
        auto_help.setWordWrap(True)
        save = mark_primary(QPushButton(S.SETTINGS_SAVE))
        save.clicked.connect(lambda _c=False: self.save())
        self._tg.toggled.connect(self._sync_tg_children)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(help_lbl)
        layout.addLayout(grid)
        layout.addWidget(self._tg)
        layout.addWidget(self._autostart)
        layout.addWidget(auto_help)
        layout.addWidget(save, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self._status)
        self.reload()

    def reload(self) -> None:
        prefs = load_prefs(self._ctx.root)
        self._win["logs"].setChecked(prefs.windows_logs)
        self._win["entered"].setChecked(prefs.windows_entered)
        self._win["left"].setChecked(prefs.windows_left)
        self._win["trades"].setChecked(prefs.windows_trades)
        self._tg.setChecked(prefs.telegram_enabled)
        self._tg_kind["logs"].setChecked(prefs.telegram_logs)
        self._tg_kind["entered"].setChecked(prefs.telegram_entered)
        self._tg_kind["left"].setChecked(prefs.telegram_left)
        self._tg_kind["trades"].setChecked(prefs.telegram_trades)
        self._autostart.setChecked(prefs.start_with_windows)
        self._sync_tg_children(self._tg.isChecked())

    def save(self) -> None:
        prefs = NotifyPrefs(
            windows_logs=self._win["logs"].isChecked(),
            windows_entered=self._win["entered"].isChecked(),
            windows_left=self._win["left"].isChecked(),
            windows_trades=self._win["trades"].isChecked(),
            telegram_enabled=self._tg.isChecked(),
            telegram_logs=self._tg_kind["logs"].isChecked(),
            telegram_entered=self._tg_kind["entered"].isChecked(),
            telegram_left=self._tg_kind["left"].isChecked(),
            telegram_trades=self._tg_kind["trades"].isChecked(),
            start_with_windows=self._autostart.isChecked(),
        )
        save_prefs(self._ctx.root, prefs)
        set_autostart(prefs.start_with_windows)
        self._sync_host_flags(prefs)
        self._status.setText(S.NOTIFY_SAVED)
        if self._on_saved is not None:
            self._on_saved()

    def _sync_host_flags(self, prefs: NotifyPrefs) -> None:
        token, chat = load_telegram_creds()
        if not token or not chat:
            return
        client = try_open_host_client(self._ctx.settings_path)
        if client is None:
            return
        client.put_telegram(
            {
                "bot_token": token,
                "chat_id": chat,
                "trade_alerts": prefs.windows_trades,
                "telegram_enabled": prefs.telegram_enabled,
                "telegram_trades": prefs.telegram_trades,
            }
        )

    def _sync_tg_children(self, enabled: bool) -> None:
        for box in self._tg_kind.values():
            box.setEnabled(enabled)
