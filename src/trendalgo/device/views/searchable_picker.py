"""Searchable dropdown: type to filter a fixed list, or enter a custom value when allowed."""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QCompleter, QWidget

from trendalgo.device import strings as S
from trendalgo.device.fields import LIVE_V1_INDICATORS
from trendalgo.exchanges.static_kraken_usd import KRAKEN_USD_PAIRS


def filter_picker_choices(query: str, choices: Sequence[str]) -> tuple[str, ...]:
    """Case-insensitive substring filter. Empty query returns the full list."""
    needle = query.strip().upper()
    if not needle:
        return tuple(choices)
    return tuple(item for item in choices if needle in item.upper())


class SearchablePicker(QComboBox):
    """Editable combo with popup completion (searchable list for device forms)."""

    def __init__(
        self,
        choices: Sequence[str],
        *,
        placeholder: str = "",
        allow_custom: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._all_choices = tuple(choices)
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.addItems(list(self._all_choices))
        line = self.lineEdit()
        if line is not None:
            line.setPlaceholderText(placeholder)
            if not allow_custom:
                line.setClearButtonEnabled(False)
        completer = QCompleter(list(self._all_choices), self)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.setCompleter(completer)
        if not allow_custom:
            self.currentTextChanged.connect(self._clamp_to_known)

    def text(self) -> str:
        return self.currentText()

    def set_text(self, value: str) -> None:
        self.setCurrentText(value)

    def setText(self, value: str) -> None:  # noqa: N802 — match QLineEdit for form tests
        self.set_text(value)

    def _clamp_to_known(self, text: str) -> None:
        if text in self._all_choices:
            return
        match = filter_picker_choices(text, self._all_choices)
        if len(match) == 1:
            self.blockSignals(True)
            self.setCurrentText(match[0])
            self.blockSignals(False)


def pair_picker(parent: QWidget | None = None) -> SearchablePicker:
    return SearchablePicker(
        KRAKEN_USD_PAIRS,
        placeholder=S.PAIR_PICKER_PLACEHOLDER,
        allow_custom=True,
        parent=parent,
    )


def indicator_picker(parent: QWidget | None = None) -> SearchablePicker:
    return SearchablePicker(
        LIVE_V1_INDICATORS,
        placeholder="",
        allow_custom=False,
        parent=parent,
    )
