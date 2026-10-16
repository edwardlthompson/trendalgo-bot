"""Resumable wizard state: which steps are done, in order. The file holds step IDs only, no secrets.

A step finishes only when its checks return no problems. The state is written under the profile
lock, so a second window cannot write it at the same time (D3).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from pathlib import Path

from trendalgo.device.lock import ProfileLock
from trendalgo.device.profile import ProfileError, read_json, write_json
from trendalgo.device.wizard.content import STEPS
from trendalgo.device.wizard.validators import Problem

WIZARD_FILE = "wizard.json"
STEP_IDS: tuple[str, ...] = tuple(step.step_id for step in STEPS)


class WizardError(RuntimeError):
    """A step was finished out of order, or the state was saved without the profile lock."""


@dataclass(frozen=True)
class WizardState:
    done: tuple[str, ...] = ()

    def next_step(self) -> str | None:
        return next((step_id for step_id in STEP_IDS if step_id not in self.done), None)

    def complete(self, step_id: str) -> WizardState:
        if step_id != self.next_step():
            raise WizardError(f"{step_id} is not the next step")
        return replace(self, done=(*self.done, step_id))

    def rewind(self) -> WizardState:
        """Un-finish the last step so the owner can check it again. Nothing is saved here."""
        if not self.done:
            raise WizardError("no finished step to go back to")
        return replace(self, done=self.done[:-1])


def advance(
    state: WizardState, step_id: str, problems: Sequence[Problem]
) -> tuple[WizardState, list[Problem]]:
    """Finish a step only when its checks pass. Returns the state and the reasons it did not move."""
    if problems:
        return state, list(problems)
    return state.complete(step_id), []


def load_state(path: Path) -> WizardState:
    data = read_json(path)
    if data is None:
        return WizardState()
    done = data.get("done")
    if not isinstance(done, list) or not all(isinstance(item, str) for item in done):
        raise ProfileError(f"{path.name} has no list of finished steps. Move it aside first.")
    if tuple(done) != STEP_IDS[: len(done)]:
        raise ProfileError(f"{path.name} lists steps out of order. Move it aside first.")
    return WizardState(tuple(done))


def save_state(path: Path, state: WizardState, lock: ProfileLock) -> None:
    if not lock.held:
        raise WizardError("the profile lock must be held before the wizard state is saved")
    write_json(path, {"done": list(state.done)})
