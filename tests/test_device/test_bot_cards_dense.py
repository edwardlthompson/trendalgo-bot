"""Dense bot card rows include strategy and disabled host actions."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

from PySide6.QtWidgets import QPushButton  # noqa: E402
from pytestqt.qtbot import QtBot  # noqa: E402

from trendalgo.device.rows import bot_rows  # noqa: E402
from trendalgo.device.views.bot_cards import BotCardList  # noqa: E402


def test_bot_rows_include_strategy_and_pnl() -> None:
    rows = bot_rows(
        [
            {
                "label": "Bot-1",
                "pair": "BTC/USD",
                "enabled": True,
                "equity_usd": 1000,
                "strategy_id": "RSI",
                "realized_pnl_usd": 12.5,
                "unrealized_pnl_usd": -3.0,
            }
        ]
    )
    assert rows[0].strategy == "RSI"
    assert rows[0].realized.startswith("$")
    assert rows[0].unrealized.startswith("-$")


def test_bot_card_actions_are_disabled_without_host(qtbot: QtBot) -> None:
    widget = BotCardList()
    qtbot.addWidget(widget)
    widget.set_bots(
        bot_rows([{"label": "A", "pair": "ETH/USD", "enabled": False, "equity_usd": 50}])
    )
    buttons = widget.findChildren(QPushButton)
    assert buttons
    assert all(not button.isEnabled() for button in buttons)


def test_bot_card_actions_enable_when_host_linked(qtbot: QtBot) -> None:
    widget = BotCardList()
    qtbot.addWidget(widget)
    widget.set_host_controls(True, on_command=lambda _a, _b: None)
    widget.set_bots(
        bot_rows([{"label": "A", "pair": "ETH/USD", "enabled": True, "equity_usd": 50}])
    )
    buttons = widget.findChildren(QPushButton)
    assert buttons
    assert all(button.isEnabled() for button in buttons)
