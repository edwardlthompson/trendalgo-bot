"""Glossary popup builds without plain-text editor stacks."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

from PySide6.QtWidgets import QApplication, QDialog, QLabel, QPlainTextEdit, QWidget  # noqa: E402
from pytestqt.qtbot import QtBot  # noqa: E402

from trendalgo.device.views import glossary_popup as gp  # noqa: E402


def test_glossary_popup_uses_labels(qtbot: QtBot, monkeypatch: pytest.MonkeyPatch) -> None:
    class Entry:
        id = "MININDEX"
        title = "Minimum Index"
        category = "Statistic Functions"
        short = "Index offset of lowest value."
        long = "MININDEX locates where the rolling minimum occurred."
        formula = "MININDEX_t = argmin(Price)"

    monkeypatch.setattr(gp, "load_glossary", lambda: ([], None))
    monkeypatch.setattr(gp, "find_glossary_entry", lambda *_a, **_k: Entry())

    held: list[QDialog] = []
    real_init = QDialog.__init__

    def tracking_init(self: QDialog, parent: QWidget | None = None) -> None:
        real_init(self, parent)
        held.append(self)

    monkeypatch.setattr(QDialog, "__init__", tracking_init)
    monkeypatch.setattr(QDialog, "exec", lambda self: 0)

    parent = QWidget()
    qtbot.addWidget(parent)
    gp.show_glossary_popup(parent, "MININDEX")
    assert held
    dialog = held[-1]
    assert dialog.findChildren(QPlainTextEdit) == []
    labels = [lab.text() for lab in dialog.findChildren(QLabel)]
    assert any("Minimum Index" in t for t in labels)
    assert any("Statistic Functions" in t for t in labels)
    assert any("Chart & math" in t for t in labels)
    assert any("argmin" in t for t in labels)
    assert not any(t == "Index offset of lowest value." for t in labels)
    _ = QApplication.instance()


def test_glossary_tooltip_has_title_and_category(monkeypatch: pytest.MonkeyPatch) -> None:
    class Entry:
        id = "RSI"
        title = "Relative Strength Index"
        category = "Momentum Indicators"
        short = "unused"

    monkeypatch.setattr(gp, "load_glossary", lambda: ([], None))
    monkeypatch.setattr(gp, "find_glossary_entry", lambda *_a, **_k: Entry())
    tip = gp.glossary_tooltip("RSI")
    assert tip == "Relative Strength Index · Momentum Indicators"


def test_formula_block_has_heading() -> None:
    frame = gp._formula_block("A = B + C")
    texts = [lab.text() for lab in frame.findChildren(QLabel)]
    assert any("Formula" in t for t in texts)
    assert any("A = B + C" in t for t in texts)
