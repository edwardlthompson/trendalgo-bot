"""Wizard Back: un-finish the last saved step, save that, and never write without the profile lock.

Skipped when PySide6 or pytest-qt is missing. Helpers mirror test_wizard_window.py.
"""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

from pytestqt.qtbot import QtBot  # noqa: E402

from trendalgo.device.context import DeviceContext  # noqa: E402
from trendalgo.device.lock import ProfileLock  # noqa: E402
from trendalgo.device.profile import read_json, write_json  # noqa: E402
from trendalgo.device.wizard import strings as W  # noqa: E402
from trendalgo.device.wizard.content import STEPS  # noqa: E402
from trendalgo.device.wizard.credentials import MemoryCredentialStore  # noqa: E402
from trendalgo.device.wizard.pages import KeyPage  # noqa: E402
from trendalgo.device.wizard.state import WIZARD_FILE, WizardError, WizardState  # noqa: E402
from trendalgo.device.wizard.view import WizardDialog  # noqa: E402


@pytest.fixture
def lock(ctx: DeviceContext) -> Iterator[ProfileLock]:
    held = ProfileLock(ctx.lock_path)
    held.acquire()
    yield held
    held.release()


def _open(
    qtbot: QtBot, ctx: DeviceContext, lock: ProfileLock, store: MemoryCredentialStore
) -> WizardDialog:
    dialog = WizardDialog(ctx, lock, store)
    qtbot.addWidget(dialog)
    return dialog


def _seed(ctx: DeviceContext, done: list[str]) -> None:
    write_json(ctx.root / WIZARD_FILE, {"done": done})


def test_rewind_removes_only_the_last_finished_step() -> None:
    assert WizardState(("W0", "W1")).rewind() == WizardState(("W0",))
    with pytest.raises(WizardError):
        WizardState().rewind()


def test_back_is_off_before_any_step_is_finished(
    qtbot: QtBot, ctx: DeviceContext, lock: ProfileLock
) -> None:
    dialog = _open(qtbot, ctx, lock, MemoryCredentialStore())
    assert not dialog._back.isEnabled()


def test_back_unfinishes_the_last_step_and_saves_that(
    qtbot: QtBot, ctx: DeviceContext, lock: ProfileLock
) -> None:
    _seed(ctx, ["W0", "W1"])
    dialog = _open(qtbot, ctx, lock, MemoryCredentialStore())
    assert dialog._back.isEnabled()
    dialog._back.click()
    assert dialog.state.done == ("W0",)
    assert read_json(ctx.root / WIZARD_FILE) == {"done": ["W0"]}
    assert isinstance(dialog._page, KeyPage)
    assert dialog._progress.text().startswith("Step 2 of 6")


def test_back_from_the_finished_screen_reopens_the_last_step(
    qtbot: QtBot, ctx: DeviceContext, lock: ProfileLock
) -> None:
    every = [step.step_id for step in STEPS]
    _seed(ctx, every)
    dialog = _open(qtbot, ctx, lock, MemoryCredentialStore())
    assert dialog._page is None
    dialog._back.click()
    assert dialog.state.done == tuple(every[:-1])
    assert dialog._page is not None
    assert dialog._continue.isEnabled()


def test_back_without_the_profile_lock_changes_nothing(qtbot: QtBot, ctx: DeviceContext) -> None:
    _seed(ctx, ["W0"])
    dialog = _open(qtbot, ctx, ProfileLock(ctx.lock_path), MemoryCredentialStore())
    dialog._back.click()
    assert dialog.state.done == ("W0",)
    assert read_json(ctx.root / WIZARD_FILE) == {"done": ["W0"]}
    assert "could not be saved" in dialog._problem.text()


def test_back_is_off_when_the_saved_state_is_corrupt(
    qtbot: QtBot, ctx: DeviceContext, lock: ProfileLock
) -> None:
    path = ctx.root / WIZARD_FILE
    path.write_text("{not json", encoding="utf-8")
    dialog = _open(qtbot, ctx, lock, MemoryCredentialStore())
    assert not dialog._back.isEnabled()
    assert path.read_text(encoding="utf-8") == "{not json"
    assert W.CONTINUE in dialog._continue.text()
