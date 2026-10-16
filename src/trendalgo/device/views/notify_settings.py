"""Settings section: alert channel toggles + Start with Windows + Telegram wizard."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QLabel, QPushButton, QVBoxLayout, QWidget

from trendalgo.device import strings as S
from trendalgo.device.autostart import set_enabled as set_autostart
from trendalgo.device.context import DeviceContext
from trendalgo.device.host_session import try_open_host_client
from trendalgo.device.notify_prefs import NotifyPrefs, load_prefs, save_prefs
from trendalgo.device.telegram_vault import load_telegram_creds
from trendalgo.device.views.telegram_wizard import TelegramWizardDialog
from trendalgo.device.views.widgets import mark_primary, section_title


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
        self._watch = QCheckBox(S.NOTIFY_WATCHLIST)
        self._qual = QCheckBox(S.NOTIFY_QUALIFIED)
        self._trade = QCheckBox(S.NOTIFY_TRADES)
        self._tg = QCheckBox(S.NOTIFY_TELEGRAM)
        self._tg_watch = QCheckBox(S.NOTIFY_TG_WATCHLIST)
        self._tg_qual = QCheckBox(S.NOTIFY_TG_QUALIFIED)
        self._tg_trade = QCheckBox(S.NOTIFY_TG_TRADES)
        self._autostart = QCheckBox(S.NOTIFY_START_WINDOWS)
        self._status = QLabel()
        help_lbl = QLabel(S.NOTIFY_SECTION_HELP)
        help_lbl.setObjectName("hint")
        help_lbl.setWordWrap(True)
        auto_help = QLabel(S.NOTIFY_START_WINDOWS_HELP)
        auto_help.setObjectName("hint")
        auto_help.setWordWrap(True)
        save = mark_primary(QPushButton(S.SETTINGS_SAVE))
        save.clicked.connect(lambda _c=False: self.save())
        wizard = QPushButton(S.NOTIFY_TELEGRAM_WIZARD)
        wizard.clicked.connect(lambda _c=False: self._open_wizard())
        self._tg.toggled.connect(self._sync_tg_children)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(section_title(S.NOTIFY_SECTION))
        layout.addWidget(help_lbl)
        for box in (
            self._watch,
            self._qual,
            self._trade,
            self._tg,
            self._tg_watch,
            self._tg_qual,
            self._tg_trade,
            self._autostart,
        ):
            layout.addWidget(box)
        layout.addWidget(auto_help)
        layout.addWidget(wizard, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(save, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self._status)
        self.reload()

    def reload(self) -> None:
        prefs = load_prefs(self._ctx.root)
        self._watch.setChecked(prefs.watchlist_alerts)
        self._qual.setChecked(prefs.qualified_alerts)
        self._trade.setChecked(prefs.trade_alerts)
        self._tg.setChecked(prefs.telegram_enabled)
        self._tg_watch.setChecked(prefs.telegram_watchlist)
        self._tg_qual.setChecked(prefs.telegram_qualified)
        self._tg_trade.setChecked(prefs.telegram_trades)
        self._autostart.setChecked(prefs.start_with_windows)
        self._sync_tg_children(self._tg.isChecked())

    def save(self) -> None:
        prefs = NotifyPrefs(
            watchlist_alerts=self._watch.isChecked(),
            qualified_alerts=self._qual.isChecked(),
            trade_alerts=self._trade.isChecked(),
            telegram_enabled=self._tg.isChecked(),
            telegram_watchlist=self._tg_watch.isChecked(),
            telegram_qualified=self._tg_qual.isChecked(),
            telegram_trades=self._tg_trade.isChecked(),
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
                "trade_alerts": prefs.trade_alerts,
                "telegram_enabled": prefs.telegram_enabled,
                "telegram_trades": prefs.telegram_trades,
            }
        )

    def _sync_tg_children(self, enabled: bool) -> None:
        for box in (self._tg_watch, self._tg_qual, self._tg_trade):
            box.setEnabled(enabled)

    def _open_wizard(self) -> None:
        TelegramWizardDialog(self._ctx, self).exec()
