"""Calendar API setup wizard (CoinMarketCal + Coindar)."""

from __future__ import annotations

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from trendalgo.device import strings as S
from trendalgo.device.calendar import vault
from trendalgo.device.calendar.providers import coindar, coinmarketcal
from trendalgo.device.calendar.providers.coinmarketcal import ProviderError
from trendalgo.device.calendar.wizard_content import STEPS
from trendalgo.device.views.widgets import clear_problem, mark_primary, problem_label, show_problem
from trendalgo.device.wizard.credentials import CredentialError, CredentialStore, open_store


class CalendarWizardDialog(QDialog):
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        store: CredentialStore | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(S.CAL_WIZARD_TITLE)
        self.resize(520, 420)
        self._store = store
        self._index = 0
        self._cmc_ok = False
        self._coindar_ok = False
        self._title = QLabel()
        self._title.setObjectName("sectionTitle")
        self._body = QLabel()
        self._body.setWordWrap(True)
        self._secret_label = QLabel(S.CAL_WIZARD_KEY)
        self._secret = QLineEdit()
        self._secret.setEchoMode(QLineEdit.EchoMode.Password)
        self._problem = problem_label()
        self._status = QLabel()
        self._status.setObjectName("hint")
        self._status.setWordWrap(True)
        self._open_docs = QPushButton(S.CAL_WIZARD_OPEN_DOCS)
        self._open_docs.clicked.connect(lambda _c=False: self._open_docs_url())
        self._test_btn = QPushButton(S.CAL_WIZARD_TEST)
        self._test_btn.clicked.connect(lambda _c=False: self._test())
        self._save_btn = mark_primary(QPushButton(S.CAL_WIZARD_SAVE))
        self._save_btn.clicked.connect(lambda _c=False: self._save())
        provider = QHBoxLayout()
        provider.addWidget(self._open_docs)
        provider.addWidget(self._test_btn)
        provider.addWidget(self._save_btn)
        provider.addStretch(1)
        buttons = QDialogButtonBox()
        self._back = buttons.addButton(S.CAL_WIZARD_BACK, QDialogButtonBox.ButtonRole.ActionRole)
        self._skip = buttons.addButton(S.CAL_WIZARD_SKIP, QDialogButtonBox.ButtonRole.ActionRole)
        self._next = buttons.addButton(S.CAL_WIZARD_NEXT, QDialogButtonBox.ButtonRole.AcceptRole)
        self._back.clicked.connect(lambda _c=False: self._go(-1))
        self._skip.clicked.connect(lambda _c=False: self._go(1))
        self._next.clicked.connect(lambda _c=False: self._go(1))
        layout = QVBoxLayout(self)
        layout.addWidget(self._title)
        layout.addWidget(self._body)
        layout.addWidget(self._secret_label)
        layout.addWidget(self._secret)
        layout.addLayout(provider)
        layout.addWidget(self._problem)
        layout.addWidget(self._status)
        layout.addStretch(1)
        layout.addWidget(buttons)
        self._render()

    def _vault(self) -> CredentialStore:
        return self._store if self._store is not None else open_store()

    def _render(self) -> None:
        step = STEPS[self._index]
        self._title.setText(step.title)
        self._body.setText("\n\n".join(step.body))
        provider = step.step_id in {"W-CAL-1", "W-CAL-2"}
        self._secret_label.setVisible(provider)
        self._secret.setVisible(provider)
        self._open_docs.setVisible(provider)
        self._test_btn.setVisible(provider)
        self._save_btn.setVisible(provider)
        self._secret_label.setText(
            S.CAL_WIZARD_TOKEN if step.step_id == "W-CAL-2" else S.CAL_WIZARD_KEY
        )
        self._secret.clear()
        self._back.setEnabled(self._index > 0)
        self._next.setText(
            S.CAL_WIZARD_FINISH if self._index >= len(STEPS) - 1 else S.CAL_WIZARD_NEXT
        )
        self._status.clear()
        clear_problem(self._problem)

    def _go(self, delta: int) -> None:
        nxt = self._index + delta
        if nxt < 0:
            return
        if nxt >= len(STEPS):
            self.accept()
            return
        self._index = nxt
        self._render()

    def _open_docs_url(self) -> None:
        step = STEPS[self._index]
        if step.sources:
            QDesktopServices.openUrl(QUrl(step.sources[0].url))

    def _test(self) -> None:
        secret = self._secret.text().strip()
        if not secret:
            show_problem(self._problem, S.CAL_WIZARD_TEST_FAIL.format(detail="empty"))
            return
        try:
            if STEPS[self._index].step_id == "W-CAL-1":
                coinmarketcal.test_key(secret)
                self._cmc_ok = True
            else:
                coindar.test_token(secret)
                self._coindar_ok = True
            clear_problem(self._problem)
            self._status.setText(S.CAL_WIZARD_TEST_OK)
        except ProviderError as exc:
            show_problem(self._problem, S.CAL_WIZARD_TEST_FAIL.format(detail=str(exc)))

    def _save(self) -> None:
        step_id = STEPS[self._index].step_id
        ok = self._cmc_ok if step_id == "W-CAL-1" else self._coindar_ok
        if not ok:
            show_problem(self._problem, S.CAL_WIZARD_NEED_TEST)
            return
        secret = self._secret.text().strip()
        try:
            if step_id == "W-CAL-1":
                vault.write_cmc_key(secret, self._vault())
            else:
                vault.write_coindar_token(secret, self._vault())
            self._status.setText(S.CAL_WIZARD_SAVED)
            clear_problem(self._problem)
        except CredentialError as exc:
            show_problem(self._problem, str(exc))
