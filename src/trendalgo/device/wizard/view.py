"""The setup wizard window: one step at a time, saved after each step, so it can be resumed.

The window writes the wizard state under the profile lock it was given. Back un-finishes the last
saved step and saves that. A corrupt state file is shown and never overwritten: Continue and Back
stay disabled until the owner moves the file aside.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from trendalgo.device.context import DeviceContext
from trendalgo.device.lock import ProfileLock
from trendalgo.device.profile import ProfileError, read_json
from trendalgo.device.settings_model import settings_from_document
from trendalgo.device.views.widgets import clear_problem, mark_primary, problem_label, show_problem
from trendalgo.device.wizard import strings as W
from trendalgo.device.wizard.content import STEPS
from trendalgo.device.wizard.credentials import CredentialStore
from trendalgo.device.wizard.model import Step
from trendalgo.device.wizard.pages import (
    AckPage,
    KeyPage,
    PairPage,
    PracticePage,
    StepPage,
)
from trendalgo.device.wizard.state import (
    STEP_IDS,
    WIZARD_FILE,
    WizardError,
    WizardState,
    advance,
    load_state,
    save_state,
)

KEY_STEP = "W1"
PRACTICE_STEP = "W2"
CAPACITY_STEP = "W3"
PAIR_STEP = "W4"


class WizardDialog(QDialog):
    def __init__(
        self,
        ctx: DeviceContext,
        lock: ProfileLock,
        store: CredentialStore,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(W.APP_TITLE)
        self.resize(760, 680)
        self._ctx = ctx
        self._lock = lock
        self._store = store
        self._path = ctx.root / WIZARD_FILE
        self._page: StepPage | None = None
        self._state = WizardState()
        self._progress = QLabel()
        self._progress.setObjectName("sectionTitle")
        self._progress.setWordWrap(True)
        self._problem = problem_label()
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._back = QPushButton(W.BACK)
        self._back.clicked.connect(lambda _checked=False: self.back_step())
        self._continue = mark_primary(QPushButton(W.CONTINUE))
        self._continue.setDefault(True)
        self._continue.clicked.connect(lambda _checked=False: self.continue_step())
        buttons = QHBoxLayout()
        buttons.addWidget(self._back)
        buttons.addStretch(1)
        buttons.addWidget(self._continue)
        layout = QVBoxLayout(self)
        layout.addWidget(self._progress)
        layout.addWidget(self._problem)
        layout.addWidget(self._scroll, 1)
        layout.addLayout(buttons)
        try:
            self._state = load_state(self._path)
        except ProfileError as exc:
            show_problem(self._problem, str(exc))
            self._back.setEnabled(False)
            self._continue.setEnabled(False)
            return
        self._show_current()

    @property
    def state(self) -> WizardState:
        return self._state

    def continue_step(self) -> None:
        """Run the current step's checks. The step is saved only when every check passes."""
        step_id = self._state.next_step()
        if step_id is None or self._page is None:
            return
        state, problems = advance(self._state, step_id, self._page.checks())
        if problems:
            show_problem(self._problem, " ".join(problem.message for problem in problems))
            return
        self._save_and_show(state)

    def back_step(self) -> None:
        """Go back one step: un-finish the last saved step and save that. Nothing else changes."""
        if not self._state.done:
            return
        self._save_and_show(self._state.rewind())

    def _save_and_show(self, state: WizardState) -> None:
        try:
            save_state(self._path, state, self._lock)
        except (OSError, WizardError) as exc:
            reason = getattr(exc, "strerror", None) or str(exc)
            show_problem(self._problem, W.SAVE_FAILED.format(reason=reason))
            return
        self._state = state
        self._show_current()

    def _show_current(self) -> None:
        clear_problem(self._problem)
        self._back.setEnabled(bool(self._state.done))
        step_id = self._state.next_step()
        if step_id is None:
            self._page = None
            self._progress.setText(W.DONE_TITLE)
            done = QLabel(W.DONE_BODY)
            done.setWordWrap(True)
            self._scroll.setWidget(done)
            self._continue.setEnabled(False)
            return
        step = next(item for item in STEPS if item.step_id == step_id)
        number = STEP_IDS.index(step_id) + 1
        self._progress.setText(
            W.PROGRESS.format(number=number, total=len(STEP_IDS), title=step.title)
        )
        self._page = self._make_page(step)
        self._scroll.setWidget(self._page)
        self._continue.setEnabled(True)

    def _make_page(self, step: Step) -> StepPage:
        if step.step_id == KEY_STEP:
            return KeyPage(step)
        if step.step_id == PRACTICE_STEP:
            return PracticePage(step, self._ctx.root, self._store)
        if step.step_id == PAIR_STEP:
            owner_id, host_url = self._saved_host()
            return PairPage(step, owner_id, host_url, self._store)
        return AckPage(step, capacity_help=step.step_id == CAPACITY_STEP)

    def _saved_host(self) -> tuple[str | None, str]:
        """Owner ID and host address from Settings. A bad settings file is reported on Settings."""
        try:
            settings = settings_from_document(read_json(self._ctx.settings_path))
        except ProfileError:
            return None, ""
        if settings is None:
            return None, ""
        return settings.owner_id, settings.host_url
