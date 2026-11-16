"""Alpaca paper keys wizard: how-to → Key ID + Secret → Test → CredMgr."""

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
from trendalgo.device.alpaca_vault import (
    clear_alpaca_creds,
    load_alpaca_creds,
    save_alpaca_creds,
)
from trendalgo.device.alpaca_verify import verify_alpaca_keys
from trendalgo.device.views.widgets import (
    clear_problem,
    field,
    mark_primary,
    problem_label,
    show_problem,
)
from trendalgo.device.wizard.credentials import CredentialError, open_store

ALPACA_DASHBOARD_URL = "https://app.alpaca.markets"


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


class AlpacaWizardDialog(QDialog):
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        root: object | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(S.ALPACA_WIZARD_TITLE)
        from pathlib import Path

        from trendalgo.device.dialog_geometry import (
            bind_dialog_geometry,
            enable_minmax,
            restore_dialog_geometry,
        )

        enable_minmax(self)
        profile = Path(str(root)) if root is not None else None
        if profile is None:
            self.resize(520, 520)
        else:
            restore_dialog_geometry(profile, self, "alpaca_wizard", default_w=520, default_h=520)
            bind_dialog_geometry(profile, self, "alpaca_wizard")
        self._key = QLineEdit()
        self._key.setEchoMode(QLineEdit.EchoMode.Password)
        self._secret = QLineEdit()
        self._secret.setEchoMode(QLineEdit.EchoMode.Password)
        self._problem = problem_label()
        self._status = QLabel()
        self._status.setWordWrap(True)
        intro = QLabel(S.ALPACA_WIZARD_INTRO)
        intro.setWordWrap(True)
        open_dash = QPushButton(S.ALPACA_WIZARD_OPEN)
        open_dash.clicked.connect(
            lambda _c=False: QDesktopServices.openUrl(QUrl(ALPACA_DASHBOARD_URL))
        )
        test = QPushButton(S.ALPACA_WIZARD_TEST)
        test.clicked.connect(lambda _c=False: self._test())
        save = mark_primary(QPushButton(S.ALPACA_WIZARD_SAVE))
        save.clicked.connect(lambda _c=False: self._save())
        remove = QPushButton(S.ALPACA_WIZARD_REMOVE)
        remove.clicked.connect(lambda _c=False: self._remove())
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        body = QWidget()
        col = QVBoxLayout(body)
        col.setContentsMargins(0, 0, 0, 0)
        col.addWidget(intro)
        col.addWidget(_step_heading(S.ALPACA_WIZARD_STEP1, S.ALPACA_WIZARD_STEP1_HELP))
        col.addWidget(open_dash, alignment=Qt.AlignmentFlag.AlignLeft)
        col.addWidget(_step_heading(S.ALPACA_WIZARD_STEP2))
        col.addWidget(field(S.ALPACA_WIZARD_KEY, self._key))
        col.addWidget(field(S.ALPACA_WIZARD_SECRET, self._secret))
        col.addWidget(_step_heading(S.ALPACA_WIZARD_STEP3))
        col.addWidget(test, alignment=Qt.AlignmentFlag.AlignLeft)
        col.addWidget(save, alignment=Qt.AlignmentFlag.AlignLeft)
        col.addWidget(remove, alignment=Qt.AlignmentFlag.AlignLeft)
        col.addWidget(self._problem)
        col.addWidget(self._status)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(scroll.Shape.NoFrame)
        scroll.setWidget(body)
        layout = QVBoxLayout(self)
        layout.addWidget(scroll)
        layout.addWidget(buttons)
        self._prefill()

    def _prefill(self) -> None:
        key, secret = load_alpaca_creds()
        if key:
            self._key.setText(key)
        if secret:
            self._secret.setText(secret)

    def _pair(self) -> tuple[str, str]:
        return self._key.text().strip(), self._secret.text().strip()

    def _test(self) -> None:
        key, secret = self._pair()
        if not key or not secret:
            show_problem(self._problem, S.ALPACA_WIZARD_NEED)
            return
        ok, msg = verify_alpaca_keys(key, secret)
        if ok:
            self._status.setText(msg or S.ALPACA_WIZARD_OK)
            clear_problem(self._problem)
        else:
            show_problem(self._problem, msg or S.ALPACA_WIZARD_FAIL)

    def _save(self) -> None:
        key, secret = self._pair()
        if not key or not secret:
            show_problem(self._problem, S.ALPACA_WIZARD_NEED)
            return
        ok, msg = verify_alpaca_keys(key, secret)
        if not ok:
            show_problem(self._problem, msg or S.ALPACA_WIZARD_FAIL)
            return
        try:
            save_alpaca_creds(key, secret, store=open_store())
        except CredentialError as exc:
            QMessageBox.critical(self, S.ALPACA_WIZARD_TITLE, str(exc))
            return
        self._status.setText(f"{S.ALPACA_WIZARD_SAVED} {msg}".strip())
        clear_problem(self._problem)

    def _remove(self) -> None:
        try:
            clear_alpaca_creds(store=open_store())
        except CredentialError as exc:
            QMessageBox.critical(self, S.ALPACA_WIZARD_TITLE, str(exc))
            return
        self._key.clear()
        self._secret.clear()
        self._status.setText(S.ALPACA_WIZARD_REMOVED)
        clear_problem(self._problem)
