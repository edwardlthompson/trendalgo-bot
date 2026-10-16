"""Glossary page: search bundled TA entries and read definitions on this PC."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from trendalgo.device import strings as S
from trendalgo.device.glossary_model import GlossaryEntry, filter_entries, load_glossary
from trendalgo.device.views.widgets import (
    EmptyState,
    TailFill,
    fill_table,
    page_header,
    read_only_table,
    section_title,
)


class GlossaryPage(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._entries, self._load_error = load_glossary()
        self._shown: list[GlossaryEntry] = []
        self._search = QLineEdit()
        self._search.setPlaceholderText(S.GLOSSARY_SEARCH_PLACEHOLDER)
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(lambda _text: self._apply_filter())
        self._count = QLabel()
        self._count.setObjectName("hint")
        self._empty = EmptyState(S.GLOSSARY_NO_MATCH_TITLE, S.GLOSSARY_NO_MATCH_BODY)
        self._load_empty = EmptyState(S.GLOSSARY_LOAD_FAILED_TITLE, S.GLOSSARY_LOAD_FAILED_BODY)
        self._table = read_only_table(S.GLOSSARY_HEADERS, S.GLOSSARY_TITLE)
        self._table.itemSelectionChanged.connect(self._show_selection)
        self._detail_title = QLabel()
        self._detail_title.setObjectName("sectionTitle")
        self._detail_title.setWordWrap(True)
        self._detail_short = QLabel()
        self._detail_short.setObjectName("hint")
        self._detail_short.setWordWrap(True)
        self._detail_long = QLabel()
        self._detail_long.setWordWrap(True)
        self._detail_formula = QPlainTextEdit()
        self._detail_formula.setReadOnly(True)
        self._detail_formula.setPlaceholderText(S.GLOSSARY_DETAIL_FORMULA)
        self._detail_related = QLabel()
        self._detail_related.setWordWrap(True)
        self._detail_related.setObjectName("hint")
        detail = QWidget()
        detail_layout = QVBoxLayout(detail)
        detail_layout.setContentsMargins(8, 0, 0, 0)
        detail_layout.addWidget(self._detail_title)
        detail_layout.addWidget(self._detail_short)
        detail_layout.addWidget(self._detail_long)
        detail_layout.addWidget(section_title(S.GLOSSARY_DETAIL_FORMULA))
        detail_layout.addWidget(self._detail_formula)
        detail_layout.addWidget(section_title(S.GLOSSARY_DETAIL_RELATED))
        detail_layout.addWidget(self._detail_related)
        detail_layout.addStretch(1)
        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._splitter.addWidget(self._table)
        self._splitter.addWidget(detail)
        self._splitter.setStretchFactor(0, 3)
        self._splitter.setStretchFactor(1, 2)
        layout = QVBoxLayout(self)
        layout.addWidget(page_header(S.GLOSSARY_TITLE, S.GLOSSARY_SUBTITLE))
        layout.addWidget(
            _search_field(S.GLOSSARY_SEARCH_LABEL, self._search, S.GLOSSARY_SEARCH_HELP)
        )
        layout.addWidget(self._count)
        layout.addWidget(self._load_empty)
        layout.addWidget(self._empty)
        layout.addWidget(self._splitter)
        self._fill = TailFill(layout, self._splitter)
        if self._load_error:
            self._load_empty.set_text(S.GLOSSARY_LOAD_FAILED_TITLE, self._load_error)
            self._load_empty.show()
            self._empty.hide()
            self._splitter.hide()
            self._search.setEnabled(False)
            self._count.setText("")
            self._fill.update(False)
            return
        self._load_empty.hide()
        self._apply_filter()

    def _apply_filter(self) -> None:
        self._shown = filter_entries(self._entries, self._search.text())
        fill_table(
            self._table,
            [(entry.title, entry.category, entry.id) for entry in self._shown],
        )
        total = len(self._entries)
        shown = len(self._shown)
        self._count.setText(S.GLOSSARY_COUNT.format(shown=shown, total=total))
        has_rows = shown > 0
        self._empty.setVisible(not has_rows)
        self._splitter.setVisible(has_rows)
        self._fill.update(has_rows)
        if has_rows:
            self._table.setCurrentCell(0, 0)
            self._show_selection()
        else:
            self._clear_detail()

    def _show_selection(self) -> None:
        row = self._table.currentRow()
        if not 0 <= row < len(self._shown):
            self._clear_detail()
            return
        entry = self._shown[row]
        self._detail_title.setText(f"{entry.title} ({entry.id})")
        self._detail_short.setText(entry.short)
        self._detail_long.setText(entry.long)
        self._detail_formula.setPlainText(entry.formula)
        if entry.related:
            self._detail_related.setText(", ".join(entry.related))
        else:
            self._detail_related.setText(S.GLOSSARY_DETAIL_NONE)

    def _clear_detail(self) -> None:
        self._detail_title.clear()
        self._detail_short.clear()
        self._detail_long.clear()
        self._detail_formula.clear()
        self._detail_related.clear()


def _search_field(label_text: str, editor: QLineEdit, help_text: str) -> QWidget:
    box = QWidget()
    layout = QVBoxLayout(box)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(QLabel(label_text))
    layout.addWidget(editor)
    editor.setAccessibleName(label_text)
    if help_text:
        editor.setAccessibleDescription(help_text)
        hint = QLabel(help_text)
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        layout.addWidget(hint)
    return box
