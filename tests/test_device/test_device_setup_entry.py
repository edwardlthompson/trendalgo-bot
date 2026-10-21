"""Settings can open the setup wizard, and the wizard reuses the window's profile lock.

Skipped when PySide6 or pytest-qt is missing.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

from PySide6.QtWidgets import QMessageBox  # noqa: E402
from pytestqt.qtbot import QtBot  # noqa: E402

from trendalgo.device import app as device_app  # noqa: E402
from trendalgo.device.context import DeviceContext  # noqa: E402
from trendalgo.device.lock import ProfileLock  # noqa: E402
from trendalgo.device.views.settings_page import SettingsPage  # noqa: E402
from trendalgo.device.wizard import credentials  # noqa: E402
from trendalgo.device.wizard.credentials import MemoryCredentialStore  # noqa: E402
from trendalgo.device.wizard.view import WizardDialog  # noqa: E402


def test_settings_hides_the_wizard_button_when_no_opener_is_given(
    qtbot: QtBot, ctx: DeviceContext
) -> None:
    page = SettingsPage(ctx)
    qtbot.addWidget(page)
    assert page._setup.isHidden()


def test_the_wizard_button_calls_the_opener_once(qtbot: QtBot, ctx: DeviceContext) -> None:
    calls: list[int] = []
    page = SettingsPage(ctx, on_setup_wizard=lambda: calls.append(1))
    qtbot.addWidget(page)
    assert not page._setup.isHidden()
    page._setup.click()
    assert calls == [1]


def test_the_opener_runs_the_wizard_with_the_window_lock(
    qtbot: QtBot, ctx: DeviceContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: dict[str, bool] = {}

    def fake_exec(self: WizardDialog) -> int:
        seen["lock_held"] = self._lock.held
        return 0

    monkeypatch.setattr(WizardDialog, "exec", fake_exec)
    monkeypatch.setattr(credentials, "open_store", lambda: MemoryCredentialStore())
    lock = ProfileLock(ctx.lock_path)
    lock.acquire()
    try:
        device_app.open_setup_wizard(ctx, lock)
        assert lock.held
    finally:
        lock.release()
    assert seen == {"lock_held": True}


def test_a_vault_error_is_shown_and_the_wizard_does_not_open(
    qtbot: QtBot, ctx: DeviceContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    shown: list[str] = []
    monkeypatch.setattr(QMessageBox, "critical", lambda *args: shown.append(str(args[2])))

    def unavailable() -> MemoryCredentialStore:
        raise credentials.CredentialError("no vault here")

    def must_not_open(self: WizardDialog) -> int:
        pytest.fail("the wizard must not open without a vault")

    monkeypatch.setattr(credentials, "open_store", unavailable)
    monkeypatch.setattr(WizardDialog, "exec", must_not_open)
    lock = ProfileLock(ctx.lock_path)
    lock.acquire()
    try:
        device_app.open_setup_wizard(ctx, lock)
    finally:
        lock.release()
    assert shown == ["no vault here"]
