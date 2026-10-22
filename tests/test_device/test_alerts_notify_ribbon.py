"""Alerts notify ribbon: toggles prefs and test callbacks."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

from pytestqt.qtbot import QtBot  # noqa: E402

from trendalgo.device import strings as S  # noqa: E402
from trendalgo.device.alert_preview import kind_master_on  # noqa: E402
from trendalgo.device.context import DeviceContext  # noqa: E402
from trendalgo.device.notify_prefs import NotifyPrefs, load_prefs, save_prefs  # noqa: E402
from trendalgo.device.views.alerts_notify_ribbon import AlertsNotifyRibbon  # noqa: E402
from trendalgo.device.views.alerts_page import AlertsPage  # noqa: E402


def test_ribbon_toggle_writes_kind_master(qtbot: QtBot, ctx: DeviceContext) -> None:
    save_prefs(
        ctx.root,
        NotifyPrefs(windows_entered=True, telegram_entered=True, telegram_enabled=True),
    )
    ribbon = AlertsNotifyRibbon(ctx.root)
    qtbot.addWidget(ribbon)
    assert kind_master_on(load_prefs(ctx.root), "entered") is True
    ribbon._toggles["entered"].click()
    assert kind_master_on(load_prefs(ctx.root), "entered") is False
    ribbon._toggles["entered"].click()
    assert kind_master_on(load_prefs(ctx.root), "entered") is True


def test_test_windows_invokes_toast(qtbot: QtBot, ctx: DeviceContext) -> None:
    toasts: list[tuple[str, str]] = []
    ribbon = AlertsNotifyRibbon(ctx.root, on_toast=lambda t, b: toasts.append((t, b)))
    qtbot.addWidget(ribbon)
    ribbon.set_kind("left")
    ribbon._test_windows()
    assert len(toasts) == 1
    assert "BTC" in toasts[0][0] or "BTC" in toasts[0][1]
    assert S.ALERTS_TEST_OK in ribbon._status.text()


def test_test_telegram_needs_setup(qtbot: QtBot, ctx: DeviceContext) -> None:
    ribbon = AlertsNotifyRibbon(ctx.root)
    qtbot.addWidget(ribbon)
    with patch(
        "trendalgo.device.views.alerts_notify_ribbon.load_telegram_creds",
        return_value=(None, None),
    ):
        ribbon._test_telegram()
    assert S.ALERTS_TEST_TG_NEED in ribbon._problem.text()


def test_test_telegram_sends_when_creds_ok(qtbot: QtBot, ctx: DeviceContext) -> None:
    save_prefs(ctx.root, NotifyPrefs(telegram_enabled=True))
    ribbon = AlertsNotifyRibbon(ctx.root)
    qtbot.addWidget(ribbon)
    ribbon.set_kind("trades")
    mock_tg = MagicMock()
    mock_tg.send_message.return_value = True
    with (
        patch(
            "trendalgo.device.views.alerts_notify_ribbon.load_telegram_creds",
            return_value=("1:tok", "42"),
        ),
        patch(
            "trendalgo.device.views.alerts_notify_ribbon.TelegramCommands",
            return_value=mock_tg,
        ),
    ):
        ribbon._test_telegram()
    mock_tg.send_message.assert_called_once()
    assert S.ALERTS_TEST_OK in ribbon._status.text()


def test_alerts_page_has_ribbon(qtbot: QtBot, ctx: DeviceContext) -> None:
    page = AlertsPage(ctx.root, on_toast=lambda _t, _b: None)
    qtbot.addWidget(page)
    assert page._ribbon is not None
    page._tabs.setCurrentIndex(2)
    assert page._ribbon._kind == "left"
