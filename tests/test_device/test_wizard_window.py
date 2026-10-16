"""Wizard window, offscreen: steps save one at a time, resume, and a bad state is never overwritten.

Skipped when PySide6 or pytest-qt is missing. The file name avoids the `*_view.*` pattern that
scripts/check-file-limits.sh reads as a UI file, so the 300-line UI limit does not apply to tests.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

from PySide6.QtWidgets import QMessageBox, QPushButton  # noqa: E402
from pytestqt.qtbot import QtBot  # noqa: E402

from trendalgo.device.context import DeviceContext  # noqa: E402
from trendalgo.device.lock import ProfileLock  # noqa: E402
from trendalgo.device.profile import read_json, write_json  # noqa: E402
from trendalgo.device.wizard import __main__ as wizard_main  # noqa: E402
from trendalgo.device.wizard import credentials  # noqa: E402
from trendalgo.device.wizard import strings as W  # noqa: E402
from trendalgo.device.wizard.content import STEPS  # noqa: E402
from trendalgo.device.wizard.credentials import (  # noqa: E402
    OWNER_SECRET_TARGET,
    PRACTICE_SECRET_TARGET,
    MemoryCredentialStore,
)
from trendalgo.device.wizard.pages import (  # noqa: E402
    AckPage,
    KeyPage,
    PairPage,
    PracticePage,
    StepPage,
)
from trendalgo.device.wizard.state import WIZARD_FILE  # noqa: E402
from trendalgo.device.wizard.view import WizardDialog  # noqa: E402


@pytest.fixture
def lock(ctx: DeviceContext) -> Iterator[ProfileLock]:
    held = ProfileLock(ctx.lock_path)
    held.acquire()
    yield held
    held.release()


@pytest.fixture
def store() -> MemoryCredentialStore:
    return MemoryCredentialStore()


def _open(
    qtbot: QtBot, ctx: DeviceContext, lock: ProfileLock, store: MemoryCredentialStore
) -> WizardDialog:
    dialog = WizardDialog(ctx, lock, store)
    qtbot.addWidget(dialog)
    return dialog


def _seed(ctx: DeviceContext, done: list[str]) -> None:
    write_json(ctx.root / WIZARD_FILE, {"done": done})


def test_a_new_wizard_starts_at_w0_and_saves_it_once_acknowledged(
    qtbot: QtBot, ctx: DeviceContext, lock: ProfileLock, store: MemoryCredentialStore
) -> None:
    dialog = _open(qtbot, ctx, lock, store)
    assert isinstance(dialog._page, AckPage)
    assert dialog._progress.text().startswith("Step 1 of 6")
    dialog._continue.click()
    assert dialog.state.done == ()
    assert W.ACK_NEEDED in dialog._problem.text()
    assert not (ctx.root / WIZARD_FILE).exists()
    dialog._page._ack.setChecked(True)
    dialog._continue.click()
    assert dialog.state.done == ("W0",)
    assert read_json(ctx.root / WIZARD_FILE) == {"done": ["W0"]}
    assert dialog._progress.text().startswith("Step 2 of 6")


def test_the_wizard_resumes_at_the_first_unfinished_step(
    qtbot: QtBot, ctx: DeviceContext, lock: ProfileLock, store: MemoryCredentialStore
) -> None:
    _seed(ctx, ["W0", "W1"])
    dialog = _open(qtbot, ctx, lock, store)
    assert dialog.state.next_step() == "W2"
    assert isinstance(dialog._page, PracticePage)
    assert dialog._progress.text().startswith("Step 3 of 6")


def test_the_key_step_needs_the_withdraw_confirmation_and_every_permission(
    qtbot: QtBot, ctx: DeviceContext, lock: ProfileLock, store: MemoryCredentialStore
) -> None:
    _seed(ctx, ["W0"])
    dialog = _open(qtbot, ctx, lock, store)
    page = dialog._page
    assert isinstance(page, KeyPage)
    dialog._continue.click()
    assert "unticked on Kraken" in dialog._problem.text()
    page._withdraw_off.setChecked(True)
    dialog._continue.click()
    assert "Modify Orders" in dialog._problem.text()
    for box in page._boxes.values():
        box.setChecked(True)
    dialog._continue.click()
    assert dialog.state.done == ("W0", "W1")
    assert read_json(ctx.root / WIZARD_FILE) == {"done": ["W0", "W1"]}


def test_the_capacity_fallback_appears_only_when_asked(
    qtbot: QtBot, ctx: DeviceContext, lock: ProfileLock, store: MemoryCredentialStore
) -> None:
    _seed(ctx, ["W0", "W1", "W2"])
    dialog = _open(qtbot, ctx, lock, store)
    page = dialog._page
    assert isinstance(page, AckPage)
    assert page._capacity.isHidden()
    button = next(
        item for item in page.findChildren(QPushButton) if item.text() == W.CAPACITY_BUTTON
    )
    button.click()
    assert not page._capacity.isHidden()
    assert "Path B" in page._capacity.text()


def test_the_practice_step_saves_only_after_the_practice_host_passes(
    qtbot: QtBot, ctx: DeviceContext, lock: ProfileLock, store: MemoryCredentialStore
) -> None:
    _seed(ctx, ["W0", "W1"])
    dialog = _open(qtbot, ctx, lock, store)
    assert isinstance(dialog._page, PracticePage)
    dialog._continue.click()
    assert dialog.state.done == ("W0", "W1", "W2")
    assert read_json(ctx.root / WIZARD_FILE) == {"done": ["W0", "W1", "W2"]}
    assert store.read(PRACTICE_SECRET_TARGET)


def test_pairing_needs_an_owner_id_saved_in_settings(
    qtbot: QtBot, ctx: DeviceContext, lock: ProfileLock, store: MemoryCredentialStore
) -> None:
    _seed(ctx, ["W0", "W1", "W2", "W3"])
    dialog = _open(qtbot, ctx, lock, store)
    assert isinstance(dialog._page, PairPage)
    dialog._continue.click()
    assert W.OWNER_MISSING in dialog._problem.text()


def test_a_bad_settings_file_leaves_pairing_without_an_owner_and_is_not_overwritten(
    qtbot: QtBot, ctx: DeviceContext, lock: ProfileLock, store: MemoryCredentialStore
) -> None:
    _seed(ctx, ["W0", "W1", "W2", "W3"])
    ctx.settings_path.write_text("{bad", encoding="utf-8")
    dialog = _open(qtbot, ctx, lock, store)
    assert isinstance(dialog._page, PairPage)
    dialog._continue.click()
    assert W.OWNER_MISSING in dialog._problem.text()
    assert ctx.settings_path.read_text(encoding="utf-8") == "{bad"


def test_a_plain_step_page_has_no_checks_of_its_own(qtbot: QtBot) -> None:
    page = StepPage(STEPS[0])
    qtbot.addWidget(page)
    assert page.checks() == []


def test_pairing_shows_the_loopback_refusal_and_saves_no_owner_secret(
    qtbot: QtBot, ctx: DeviceContext, lock: ProfileLock, store: MemoryCredentialStore
) -> None:
    _seed(ctx, ["W0", "W1", "W2", "W3"])
    write_json(ctx.settings_path, {"owner_id": "owner-1", "host_url": "https://host.example:8443"})
    dialog = _open(qtbot, ctx, lock, store)
    page = dialog._page
    assert isinstance(page, PairPage)
    assert page._host.text() == "https://host.example:8443"
    dialog._continue.click()
    assert "32 characters" in dialog._problem.text()
    page._secret.setText("s" * 32)
    page._code.setText("ABCD-EFGH")
    dialog._continue.click()
    assert "127.0.0.1" in dialog._problem.text()
    assert store.read(OWNER_SECRET_TARGET) is None
    assert dialog.state.done == ("W0", "W1", "W2", "W3")


def test_a_corrupt_state_file_disables_continue_and_is_never_overwritten(
    qtbot: QtBot, ctx: DeviceContext, lock: ProfileLock, store: MemoryCredentialStore
) -> None:
    path = ctx.root / WIZARD_FILE
    path.write_text("{not json", encoding="utf-8")
    dialog = _open(qtbot, ctx, lock, store)
    assert not dialog._continue.isEnabled()
    assert "Move it aside" in dialog._problem.text()
    assert path.read_text(encoding="utf-8") == "{not json"


def test_a_step_is_not_saved_without_the_profile_lock(
    qtbot: QtBot, ctx: DeviceContext, store: MemoryCredentialStore
) -> None:
    dialog = _open(qtbot, ctx, ProfileLock(ctx.lock_path), store)
    dialog._page._ack.setChecked(True)
    dialog._continue.click()
    assert dialog.state.done == ()
    assert not (ctx.root / WIZARD_FILE).exists()
    assert "could not be saved" in dialog._problem.text()


def test_when_every_step_is_saved_the_window_says_so(
    qtbot: QtBot, ctx: DeviceContext, lock: ProfileLock, store: MemoryCredentialStore
) -> None:
    _seed(ctx, [step.step_id for step in STEPS])
    dialog = _open(qtbot, ctx, lock, store)
    assert dialog._page is None
    assert dialog._progress.text() == W.DONE_TITLE
    assert not dialog._continue.isEnabled()


def test_the_entry_point_opens_the_wizard_and_releases_the_lock(
    ctx: DeviceContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(WizardDialog, "exec", lambda self: 0)
    monkeypatch.setattr(credentials, "open_store", lambda: MemoryCredentialStore())
    assert wizard_main.run(ctx.root) == 0
    again = ProfileLock(ctx.lock_path)
    again.acquire()
    again.release()


def test_the_entry_point_refuses_a_profile_another_window_holds(
    ctx: DeviceContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    shown: list[str] = []
    monkeypatch.setattr(QMessageBox, "critical", lambda *args: shown.append(str(args[2])))
    holder = ProfileLock(ctx.lock_path)
    holder.acquire()
    try:
        assert wizard_main.run(ctx.root) == 1
    finally:
        holder.release()
    assert shown and "Another TrendAlgo window" in shown[0]


def test_the_entry_point_says_so_when_the_profile_folder_cannot_be_made(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    shown: list[str] = []
    monkeypatch.setattr(QMessageBox, "critical", lambda *args: shown.append(str(args[2])))
    not_a_folder = tmp_path / "file-in-the-way"
    not_a_folder.write_text("x", encoding="utf-8")
    assert wizard_main.run(not_a_folder) == 1
    assert len(shown) == 1


def test_the_entry_point_says_so_where_the_vault_is_unavailable(
    ctx: DeviceContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    shown: list[str] = []
    monkeypatch.setattr(QMessageBox, "critical", lambda *args: shown.append(str(args[2])))

    def unavailable() -> MemoryCredentialStore:
        raise credentials.CredentialError(
            "Windows Credential Manager is only available on Windows."
        )

    monkeypatch.setattr(credentials, "open_store", unavailable)
    assert wizard_main.run(Path(ctx.root)) == 1
    assert shown == ["Windows Credential Manager is only available on Windows."]
