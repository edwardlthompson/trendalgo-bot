"""Glossary detail dialog opened from Results / Backtest indicator clicks."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFrame,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from trendalgo.device import strings as S
from trendalgo.device.glossary_model import find_glossary_entry, load_glossary

_MIN_W = 420
_PAD = 20


def show_glossary_popup(parent: QWidget, indicator: str) -> None:
    entries, error = load_glossary()
    entry = None if error else find_glossary_entry(entries, indicator)
    dialog = QDialog(parent)
    dialog.setMinimumWidth(_MIN_W)
    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(_PAD, _PAD, _PAD, _PAD)
    layout.setSpacing(12)

    if entry is None:
        dialog.setWindowTitle(S.SCANNER_GLOSSARY_MISS_TITLE)
        title = QLabel(S.SCANNER_GLOSSARY_MISS_TITLE)
        title.setObjectName("sectionTitle")
        body = QLabel(S.SCANNER_GLOSSARY_MISS_BODY.format(name=indicator or "—"))
        body.setObjectName("hint")
        body.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(body)
    else:
        dialog.setWindowTitle(entry.title)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        inner = QWidget()
        col = QVBoxLayout(inner)
        col.setContentsMargins(0, 0, 8, 0)
        col.setSpacing(12)
        title = QLabel(entry.title)
        title.setObjectName("sectionTitle")
        title_font = QFont(title.font())
        title_font.setPointSize(max(12, title_font.pointSize() + 2))
        title_font.setBold(True)
        title.setFont(title_font)
        title.setWordWrap(True)
        col.addWidget(title)
        type_line = QLabel(f"{entry.category} · {pool_label_for(entry.id)}")
        type_line.setObjectName("hint")
        type_line.setWordWrap(True)
        col.addWidget(type_line)
        if entry.long:
            long = QLabel(entry.long)
            long.setWordWrap(True)
            col.addWidget(long)
        if entry.formula:
            col.addWidget(_formula_block(entry.formula))
        col.addStretch(1)
        scroll.setWidget(inner)
        scroll.setMinimumHeight(220)
        layout.addWidget(scroll, 1)

    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
    buttons.rejected.connect(dialog.reject)
    buttons.accepted.connect(dialog.accept)
    layout.addWidget(buttons)
    dialog.adjustSize()
    dialog.exec()


def glossary_tooltip(indicator: str) -> str:
    entries, error = load_glossary()
    if error:
        return ""
    entry = find_glossary_entry(entries, indicator)
    if entry is None:
        return ""
    return f"{entry.title} · {entry.category}"


def pool_label_for(indicator_id: str) -> str:
    if str(indicator_id or "").casefold() in {"oracle-max", "oracle max"}:
        return "Baseline"
    from trendalgo.ta.strategy_pool import pool_label

    return pool_label(indicator_id)


def _formula_block(formula: str) -> QFrame:
    frame = QFrame()
    frame.setObjectName("panel")
    frame.setFrameShape(QFrame.Shape.StyledPanel)
    col = QVBoxLayout(frame)
    col.setContentsMargins(12, 10, 12, 10)
    col.setSpacing(6)
    heading = QLabel(S.GLOSSARY_DETAIL_FORMULA)
    heading.setObjectName("sectionTitle")
    col.addWidget(heading)
    body = QLabel(formula)
    body.setWordWrap(True)
    body.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    mono = QFont("Consolas")
    if mono.exactMatch() is False:
        mono = QFont("Courier New")
    mono.setStyleHint(QFont.StyleHint.Monospace)
    mono.setPointSize(max(10, body.font().pointSize()))
    body.setFont(mono)
    col.addWidget(body)
    return frame
