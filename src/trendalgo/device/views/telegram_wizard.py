"""BotFather step wizard: copy scripts → token + chat id → CredMgr + optional host sync."""

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
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from trendalgo.device import strings as S
from trendalgo.device import telegram_botfather as BF
from trendalgo.device.context import DeviceContext
from trendalgo.device.host_session import try_open_host_client
from trendalgo.device.notify_prefs import load_prefs
from trendalgo.device.telegram_vault import save_telegram_creds
from trendalgo.device.views.copy_snippet import CopySnippet
from trendalgo.device.views.widgets import (
    clear_problem,
    field,
    mark_primary,
    problem_label,
    show_problem,
)
from trendalgo.device.wizard.credentials import CredentialError, open_store
from trendalgo.notifications.telegram import TelegramCommands

BOTFATHER_URL = "https://t.me/BotFather"


def _step_heading(title: str, help_text: str = "") -> QWidget:
    box = QWidget()
    layout = QVBoxLayout(box)
    layout.setContentsMargins(0, 8, 0, 0)
    layout.setSpacing(4)
    head = QLabel(title)
    head.setObjectName("subtitle")
    layout.addWidget(head)
    if help_text:
        note = QLabel(help_text)
        note.setObjectName("hint")
        note.setWordWrap(True)
        layout.addWidget(note)
    return box


class TelegramWizardDialog(QDialog):
    def __init__(self, ctx: DeviceContext, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._ctx = ctx
        self.setWindowTitle(S.TG_WIZARD_TITLE)
        self.resize(560, 560)
        self._token = QLineEdit()
        self._token.setEchoMode(QLineEdit.EchoMode.Password)
        self._chat = QLineEdit()
        self._problem = problem_label()
        self._status = QLabel()
        self._status.setWordWrap(True)
        self.snip_newbot = CopySnippet(S.TG_WIZARD_SNIP_NEWBOT, BF.CMD_NEWBOT)
        self.snip_name = CopySnippet(S.TG_WIZARD_SNIP_NAME, BF.DISPLAY_NAME)
        self.snip_user = CopySnippet(S.TG_WIZARD_SNIP_USER, BF.USERNAME)
        self.snip_mybots = CopySnippet(S.TG_WIZARD_SNIP_MYBOTS, BF.CMD_MYBOTS)
        self.snip_start = CopySnippet(S.TG_WIZARD_SNIP_START, BF.CMD_START)
        self.snip_delete_wh = CopySnippet(
            S.TG_WIZARD_SNIP_DELETE_WH, S.TG_WIZARD_DELETE_WH_PLACEHOLDER
        )
        intro = QLabel(S.TG_WIZARD_INTRO)
        intro.setWordWrap(True)
        open_bf = QPushButton(S.TG_WIZARD_BOTFATHER)
        open_bf.clicked.connect(lambda _c=False: QDesktopServices.openUrl(QUrl(BOTFATHER_URL)))
        open_wh = QPushButton(S.TG_WIZARD_OPEN_DELETE_WH)
        open_wh.clicked.connect(lambda _c=False: self._open_delete_webhook())
        detect = QPushButton(S.TG_WIZARD_DETECT)
        detect.clicked.connect(lambda _c=False: self._detect())
        test = QPushButton(S.TG_WIZARD_TEST)
        test.clicked.connect(lambda _c=False: self._test())
        save = mark_primary(QPushButton(S.TG_WIZARD_SAVE))
        save.clicked.connect(lambda _c=False: self._save())
        self._token.textChanged.connect(lambda _t="": self._sync_delete_webhook_url())
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        body = QWidget()
        col = QVBoxLayout(body)
        col.setContentsMargins(0, 0, 0, 0)
        col.addWidget(intro)
        col.addWidget(_step_heading(S.TG_WIZARD_STEP1, S.TG_WIZARD_STEP1_HELP))
        col.addWidget(open_bf, alignment=Qt.AlignmentFlag.AlignLeft)
        for snip in (self.snip_newbot, self.snip_name, self.snip_user, self.snip_mybots):
            col.addWidget(snip)
        col.addWidget(field(S.TG_WIZARD_TOKEN, self._token))
        col.addWidget(_step_heading(S.TG_WIZARD_STEP2, S.TG_WIZARD_STEP2_HELP))
        col.addWidget(self.snip_start)
        col.addWidget(self.snip_delete_wh)
        col.addWidget(open_wh, alignment=Qt.AlignmentFlag.AlignLeft)
        col.addWidget(field(S.TG_WIZARD_CHAT, self._chat))
        col.addWidget(detect, alignment=Qt.AlignmentFlag.AlignLeft)
        col.addWidget(_step_heading(S.TG_WIZARD_STEP3))
        col.addWidget(test, alignment=Qt.AlignmentFlag.AlignLeft)
        col.addWidget(save, alignment=Qt.AlignmentFlag.AlignLeft)
        col.addWidget(self._problem)
        col.addWidget(self._status)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(scroll.Shape.NoFrame)
        scroll.setWidget(body)
        layout = QVBoxLayout(self)
        layout.addWidget(scroll)
        layout.addWidget(buttons)

    def _client(self) -> TelegramCommands:
        return TelegramCommands(token=self._token.text().strip(), chat_id=self._chat.text().strip())

    def _sync_delete_webhook_url(self) -> None:
        tg = TelegramCommands(token=self._token.text().strip(), chat_id=None)
        url = tg.api_url("deleteWebhook")
        self.snip_delete_wh.set_text(url or S.TG_WIZARD_DELETE_WH_PLACEHOLDER)

    def _open_delete_webhook(self) -> None:
        url = self.snip_delete_wh.text()
        if not url or "<TOKEN>" in url:
            show_problem(self._problem, S.TG_WIZARD_NEED_TOKEN)
            return
        QDesktopServices.openUrl(QUrl(url))

    def _detect(self) -> None:
        token = self._token.text().strip()
        if not token:
            show_problem(self._problem, S.TG_WIZARD_NEED_TOKEN)
            return
        tg = TelegramCommands(token=token, chat_id=None)
        found = tg.detect_chat_id()
        if found:
            self._chat.setText(found)
            self._status.setText(S.TG_WIZARD_OK)
            clear_problem(self._problem)
        else:
            show_problem(self._problem, S.TG_WIZARD_DETECT_FAIL)

    def _test(self) -> None:
        ok = self._client().send_message("TrendAlgo test — alerts are working.")
        if ok:
            self._status.setText(S.TG_WIZARD_OK)
            clear_problem(self._problem)
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
