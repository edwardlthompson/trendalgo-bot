"""Searchable pair and indicator pickers (offscreen Qt)."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

from PySide6.QtWidgets import QComboBox  # noqa: E402
from pytestqt.qtbot import QtBot  # noqa: E402

from trendalgo.device.fields import LIVE_V1_INDICATORS  # noqa: E402
from trendalgo.device.views.searchable_picker import (  # noqa: E402
    SearchablePicker,
    filter_picker_choices,
    indicator_picker,
    pair_picker,
)
from trendalgo.exchanges.static_kraken_usd import KRAKEN_USD_PAIRS  # noqa: E402


def test_filter_picker_choices_is_case_insensitive_substring() -> None:
    choices = ("BTC/USD", "ETH/USD", "SOL/USD")
    assert filter_picker_choices("", choices) == choices
    assert filter_picker_choices("eth", choices) == ("ETH/USD",)
    assert filter_picker_choices("/usd", choices) == choices


def test_pair_picker_lists_kraken_usd_pairs(qtbot: QtBot) -> None:
    picker = pair_picker()
    qtbot.addWidget(picker)
    assert picker.count() == len(KRAKEN_USD_PAIRS)
    assert "BTC/USD" in KRAKEN_USD_PAIRS


def test_indicator_picker_starts_with_live_v1_indicators(qtbot: QtBot) -> None:
    picker = indicator_picker()
    qtbot.addWidget(picker)
    assert picker.count() == len(LIVE_V1_INDICATORS)
    picker.set_text("macd")
    qtbot.wait(50)
    assert picker.text().casefold() == "macd".casefold() or picker.text() == "MACD"


def test_searchable_picker_accepts_custom_pair_text(qtbot: QtBot) -> None:
    picker = SearchablePicker(("BTC/USD",), allow_custom=True)
    qtbot.addWidget(picker)
    picker.set_text("CUSTOM/USD")
    assert picker.text() == "CUSTOM/USD"


def test_searchable_picker_is_editable_combo(qtbot: QtBot) -> None:
    picker = pair_picker()
    qtbot.addWidget(picker)
    assert isinstance(picker, QComboBox)
    assert picker.isEditable()
