"""BotFather step wizard: token + chat id → CredMgr + optional host sync."""

from __future__ import annotations

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from trendalgo.device import strings as S
from trendalgo.device.context import DeviceContext
from trendalgo.device.host_session import try_open_host_client
from trendalgo.device.notify_prefs import load_prefs
from trendalgo.device.telegram_vault import save_telegram_creds
from trendalgo.device.views.widgets import field, mark_primary, problem_label, show_problem
from trendalgo.device.wizard.credentials import CredentialError, open_store
from trendalgo.notifications.telegram import TelegramCommands

BOTFATHER_URL = "https://t.me/BotFather"


class TelegramWizardDialog(QDialog):
    def __init__(self, ctx: DeviceContext, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._ctx = ctx
        self.setWindowTitle(S.TG_WIZARD_TITLE)
        self.resize(480, 360)
        self._token = QLineEdit()
        self._token.setEchoMode(QLineEdit.EchoMode.Password)
        self._chat = QLineEdit()
        self._problem = problem_label()
        self._status = QLabel()
        self._status.setWordWrap(True)
        intro = QLabel(S.TG_WIZARD_INTRO)
        intro.setWordWrap(True)
        open_bf = QPushButton(S.TG_WIZARD_BOTFATHER)
        open_bf.clicked.connect(lambda _c=False: QDesktopServices.openUrl(QUrl(BOTFATHER_URL)))
        detect = QPushButton(S.TG_WIZARD_DETECT)
        detect.clicked.connect(lambda _c=False: self._detect())
        test = QPushButton(S.TG_WIZARD_TEST)
        test.clicked.connect(lambda _c=False: self._test())
        save = mark_primary(QPushButton(S.TG_WIZARD_SAVE))
        save.clicked.connect(lambda _c=False: self._save())
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(intro)
        layout.addWidget(open_bf, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(field(S.TG_WIZARD_TOKEN, self._token))
        layout.addWidget(field(S.TG_WIZARD_CHAT, self._chat))
        layout.addWidget(detect, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(test, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(save, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self._problem)
        layout.addWidget(self._status)
        layout.addWidget(buttons)

    def _client(self) -> TelegramCommands:
        return TelegramCommands(token=self._token.text().strip(), chat_id=self._chat.text().strip())

    def _detect(self) -> None:
        tg = TelegramCommands(token=self._token.text().strip(), chat_id=None)
        found = tg.detect_chat_id()
        if found:
            self._chat.setText(found)
            self._status.setText(S.TG_WIZARD_OK)
        else:
            show_problem(self._problem, S.TG_WIZARD_FAIL)

    def _test(self) -> None:
        ok = self._client().send_message("TrendAlgo test — alerts are working.")
        if ok:
            self._status.setText(S.TG_WIZARD_OK)
        else:
            show_problem(self._problem, S.TG_WIZARD_FAIL)

    def _save(self) -> None:
        token = self._token.text().strip()
        chat = self._chat.text().strip()
        if not token or not chat:
            show_problem(self._problem, S.TG_WIZARD_FAIL)
            return
        try:
            store = open_store()
            save_telegram_creds(token, chat, store=store)
        except CredentialError as exc:
            QMessageBox.critical(self, S.TG_WIZARD_TITLE, str(exc))
            return
        self._status.setText(S.TG_WIZARD_SAVED)
        client = try_open_host_client(self._ctx.settings_path)
        if client is None:
            self._status.setText(f"{S.TG_WIZARD_SAVED} {S.TG_WIZARD_SYNC_SKIP}")
            return
        prefs = load_prefs(self._ctx.root)
        resp = client.put_telegram(
            {
                "bot_token": token,
                "chat_id": chat,
                "trade_alerts": prefs.trade_alerts,
                "telegram_enabled": prefs.telegram_enabled,
                "telegram_trades": prefs.telegram_trades,
            }
        )
        if resp.ok:
            self._status.setText(f"{S.TG_WIZARD_SAVED} {S.TG_WIZARD_SYNC_OK}")
        else:
            self._status.setText(f"{S.TG_WIZARD_SAVED} {S.TG_WIZARD_SYNC_SKIP}")
