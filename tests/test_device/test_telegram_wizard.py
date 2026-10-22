"""Telegram BotFather wizard: copy snippets + detect guidance."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

from PySide6.QtWidgets import QApplication  # noqa: E402
from pytestqt.qtbot import QtBot  # noqa: E402

from trendalgo.device import strings as S  # noqa: E402
from trendalgo.device import telegram_botfather as BF  # noqa: E402
from trendalgo.device.context import DeviceContext  # noqa: E402
from trendalgo.device.views.telegram_wizard import TelegramWizardDialog  # noqa: E402


def test_wizard_exposes_botfather_copy_snippets(qtbot: QtBot, ctx: DeviceContext) -> None:
    dialog = TelegramWizardDialog(ctx)
    qtbot.addWidget(dialog)
    assert dialog.snip_newbot.text() == BF.CMD_NEWBOT
    assert dialog.snip_name.text() == BF.DISPLAY_NAME
    assert dialog.snip_user.text() == BF.USERNAME
    assert dialog.snip_mybots.text() == BF.CMD_MYBOTS
    assert dialog.snip_start.text() == BF.CMD_START
    assert "<TOKEN>" in dialog.snip_delete_wh.text()


def test_copy_newbot_puts_command_on_clipboard(qtbot: QtBot, ctx: DeviceContext) -> None:
    dialog = TelegramWizardDialog(ctx)
    qtbot.addWidget(dialog)
    assert dialog.snip_newbot.copy() is True
    clip = QApplication.clipboard()
    assert clip is not None
    assert clip.text() == BF.CMD_NEWBOT


def test_token_fills_delete_webhook_url(qtbot: QtBot, ctx: DeviceContext) -> None:
    dialog = TelegramWizardDialog(ctx)
    qtbot.addWidget(dialog)
    dialog._token.setText("99:secret")
    assert dialog.snip_delete_wh.text() == "https://api.telegram.org/bot99:secret/deleteWebhook"


def test_detect_fail_shows_start_guidance(qtbot: QtBot, ctx: DeviceContext) -> None:
    dialog = TelegramWizardDialog(ctx)
    qtbot.addWidget(dialog)
    dialog._token.setText("123:fake")
    with patch(
        "trendalgo.device.views.telegram_wizard.TelegramCommands.detect_chat_id",
        return_value=None,
    ):
        dialog._detect()
    assert S.TG_WIZARD_DETECT_FAIL in dialog._problem.text()
    assert "/start" in dialog._problem.text()


def test_detect_without_token_prompts(qtbot: QtBot, ctx: DeviceContext) -> None:
    dialog = TelegramWizardDialog(ctx)
    qtbot.addWidget(dialog)
    dialog._detect()
    assert S.TG_WIZARD_NEED_TOKEN in dialog._problem.text()
