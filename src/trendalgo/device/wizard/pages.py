"""Wizard pages, one per step. A page holds its controls and returns its own checks; the dialog moves."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

from trendalgo.device.views.widgets import field
from trendalgo.device.wizard import strings as W
from trendalgo.device.wizard.credentials import CredentialStore
from trendalgo.device.wizard.hostclient import pair_host
from trendalgo.device.wizard.model import Step
from trendalgo.device.wizard.practice import run_practice
from trendalgo.device.wizard.validators import PERMISSIONS, Problem, check_key_permissions


def _wrapped(text: str) -> QLabel:
    label = QLabel(text)
    label.setWordWrap(True)
    return label


class StepPage(QWidget):
    """Title, body text and sources. Subclasses add controls to `form` and override `checks`."""

    def __init__(self, step: Step, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        title = QLabel(step.title)
        title.setObjectName("pageTitle")
        title.setWordWrap(True)
        self.form = QVBoxLayout()
        layout = QVBoxLayout(self)
        layout.addWidget(title)
        for paragraph in step.body:
            layout.addWidget(_wrapped(paragraph))
        if step.sources:
            layout.addWidget(QLabel(W.SOURCES_HEADING))
        for source in step.sources:
            line = W.SOURCE_LINE.format(
                label=source.label, url=source.url, checked=source.verified.isoformat()
            )
            layout.addWidget(_wrapped(line))
        layout.addLayout(self.form)
        layout.addStretch(1)

    def checks(self) -> list[Problem]:
        return []


class AckPage(StepPage):
    """Text-only steps. The owner ticks the box after reading; the step cannot pass otherwise."""

    def __init__(self, step: Step, *, capacity_help: bool = False, parent: QWidget | None = None):
        super().__init__(step, parent)
        self._ack = QCheckBox(W.ACK)
        self._ack.setAccessibleName(W.ACK)
        self.form.addWidget(self._ack)
        if capacity_help:
            self._capacity = _wrapped(W.CAPACITY_TEXT)
            self._capacity.hide()
            button = QPushButton(W.CAPACITY_BUTTON)
            button.clicked.connect(lambda _checked=False: self._capacity.show())
            self.form.addWidget(button, alignment=Qt.AlignmentFlag.AlignLeft)
            self.form.addWidget(self._capacity)

    def checks(self) -> list[Problem]:
        if self._ack.isChecked():
            return []
        return [Problem("step.not_acknowledged", W.ACK_NEEDED)]


class KeyPage(StepPage):
    """W1: the owner confirms each Kraken permission, and that Withdraw Funds is off."""

    def __init__(self, step: Step, parent: QWidget | None = None) -> None:
        super().__init__(step, parent)
        self.form.addWidget(_wrapped(W.PERMISSION_HELP))
        self._boxes: dict[str, QCheckBox] = {}
        for name in PERMISSIONS:
            box = QCheckBox(name)
            box.setAccessibleName(name)
            self._boxes[name] = box
            self.form.addWidget(box)
        self._withdraw_off = QCheckBox(W.WITHDRAW_CONFIRM)
        self._withdraw_off.setAccessibleName(W.WITHDRAW_CONFIRM)
        self.form.addWidget(self._withdraw_off)

    def checks(self) -> list[Problem]:
        ticked = frozenset(name for name, box in self._boxes.items() if box.isChecked())
        problem = check_key_permissions(ticked, self._withdraw_off.isChecked())
        return [] if problem is None else [problem]


class PracticePage(StepPage):
    """W2: the practice checks run on 127.0.0.1. The step passes only when all four pass."""

    def __init__(
        self, step: Step, root: Path, store: CredentialStore, parent: QWidget | None = None
    ) -> None:
        super().__init__(step, parent)
        self._root = root
        self._store = store
        self._note = _wrapped(W.PRACTICE_NOTE)
        self.form.addWidget(self._note)

    def checks(self) -> list[Problem]:
        problems = run_practice(self._root, self._store)
        self._note.setText(W.PRACTICE_NOTE if problems else W.PRACTICE_PASSED)
        return problems


class PairPage(StepPage):
    """W4: pairs with the host. This build pairs only with the practice host on 127.0.0.1."""

    def __init__(
        self,
        step: Step,
        owner_id: str | None,
        host_url: str,
        store: CredentialStore,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(step, parent)
        self._owner_id = owner_id
        self._store = store
        self._host = QLineEdit(host_url)
        self._secret = QLineEdit()
        self._secret.setEchoMode(QLineEdit.EchoMode.Password)
        self._code = QLineEdit()
        self._code.setPlaceholderText("XXXX-XXXX")
        self.form.addWidget(_wrapped(W.PAIR_NOTE))
        self.form.addWidget(field(W.PAIR_HOST, self._host))
        self.form.addWidget(field(W.PAIR_OWNER, self._secret, W.PAIR_OWNER_HELP))
        self.form.addWidget(field(W.PAIR_CODE, self._code, W.PAIR_CODE_HELP))

    def checks(self) -> list[Problem]:
        if self._owner_id is None:
            return [Problem("owner.missing", W.OWNER_MISSING)]
        return pair_host(
            self._host.text().strip(),
            self._owner_id,
            self._secret.text(),
            self._code.text(),
            self._store,
        )
