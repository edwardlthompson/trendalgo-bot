"""Qt smoke for the Glossary page."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

from pytestqt.qtbot import QtBot  # noqa: E402

from trendalgo.device import strings as S  # noqa: E402
from trendalgo.device.glossary_model import bundled_glossary_path, load_glossary  # noqa: E402
from trendalgo.device.views.glossary_page import GlossaryPage  # noqa: E402


def test_glossary_page_loads_and_shows_adx_detail(qtbot: QtBot) -> None:
    entries, error = load_glossary()
    assert error is None
    page = GlossaryPage()
    qtbot.addWidget(page)
    page.show()
    assert page._load_error is None
    assert page._load_empty.isHidden()
    assert not page._splitter.isHidden()
    page._search.setText("ADX")
    qtbot.waitUntil(lambda: page._table.rowCount() >= 1 and "ADX" in page._detail_title.text())
    assert page._detail_formula.toPlainText().strip()


def test_glossary_page_no_match_shows_empty_state(qtbot: QtBot) -> None:
    page = GlossaryPage()
    qtbot.addWidget(page)
    page.show()
    page._search.setText("zzzznotermzzzz")
    qtbot.wait(50)
    assert not page._empty.isHidden()
    assert page._splitter.isHidden()


def test_glossary_page_load_failure_uses_empty_state(qtbot: QtBot, monkeypatch) -> None:
    monkeypatch.setattr(
        "trendalgo.device.views.glossary_page.load_glossary",
        lambda path=None: ([], "missing file"),
    )
    page = GlossaryPage()
    qtbot.addWidget(page)
    page.show()
    assert not page._load_empty.isHidden()
    assert S.GLOSSARY_LOAD_FAILED_TITLE in page._load_empty._title.text()
    assert bundled_glossary_path().is_file()
