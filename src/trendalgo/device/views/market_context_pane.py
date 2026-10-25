"""Dedicated Market Context band — horizontal equal modules, not strategy rows."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from trendalgo.device import strings as S
from trendalgo.device.views.collapsible_section import CollapsibleSection
from trendalgo.device.views.market_context_format import (
    levels_lines,
    risk_line,
    signal_line,
    structure_lines,
)
from trendalgo.device.views.market_context_gfx import (
    LevelsLadder,
    RiskBars,
    SignalGauge,
    StructureMeters,
)


class MarketContextPane(QFrame):
    """Four equal-width modules in one horizontal row."""

    collapsed_changed = Signal(bool)

    def __init__(
        self,
        *,
        expanded: bool = True,
        on_collapse: Callable[[bool], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("panel")
        self.setAccessibleName(S.MARKET_CTX_TITLE)
        self._on_collapse = on_collapse
        self._section = CollapsibleSection(S.MARKET_CTX_TITLE, expanded=expanded)
        self._subtitle = QLabel(S.MARKET_CTX_SUBTITLE)
        self._subtitle.setObjectName("hint")
        self._subtitle.setWordWrap(True)
        self._status = QLabel(S.MARKET_CTX_EMPTY)
        self._status.setObjectName("hint")
        self._status.setWordWrap(True)

        self._signal_txt = QLabel()
        self._signal_txt.setObjectName("hint")
        self._signal_txt.setWordWrap(True)
        self._levels_txt = QLabel()
        self._levels_txt.setObjectName("hint")
        self._levels_txt.setWordWrap(True)
        self._risk_txt = QLabel()
        self._risk_txt.setObjectName("hint")
        self._risk_txt.setWordWrap(True)
        self._structure_txt = QLabel()
        self._structure_txt.setObjectName("hint")
        self._structure_txt.setWordWrap(True)

        self._gauge = SignalGauge()
        self._ladder = LevelsLadder()
        self._risk_bars = RiskBars()
        self._meters = StructureMeters()

        self._modules = (
            self._module(S.MARKET_CTX_SIGNAL, self._gauge, self._signal_txt),
            self._module(S.MARKET_CTX_LEVELS, self._ladder, self._levels_txt),
            self._module(S.MARKET_CTX_RISK, self._risk_bars, self._risk_txt),
            self._module(S.MARKET_CTX_STRUCTURE, self._meters, self._structure_txt),
        )

        row = QWidget()
        row_lay = QHBoxLayout(row)
        row_lay.setContentsMargins(0, 4, 0, 0)
        row_lay.setSpacing(8)
        for mod in self._modules:
            row_lay.addWidget(mod, 1)

        body = self._section.body_layout()
        body.addWidget(self._subtitle)
        body.addWidget(self._status)
        body.addWidget(row)
        self._row = row
        self._set_content_visible(False)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self._section)
        self._section.toggled.connect(self._on_toggled)

    def _module(self, title: str, gfx: QWidget, caption: QLabel) -> QFrame:
        card = QFrame()
        card.setObjectName("marketCtxModule")
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)
        card.setMinimumHeight(220)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(10, 10, 10, 12)
        lay.setSpacing(6)
        head = QLabel(title)
        head.setObjectName("sectionTitle")
        caption.setWordWrap(True)
        caption.setMinimumHeight(44)
        caption.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        lay.addWidget(head)
        lay.addWidget(gfx, 1)
        lay.addWidget(caption, 0)
        return card

    def _on_toggled(self, expanded: bool) -> None:
        self.collapsed_changed.emit(not expanded)
        if self._on_collapse is not None:
            self._on_collapse(not expanded)

    def set_loading(self) -> None:
        self._status.setText(S.MARKET_CTX_LOADING)
        self._status.show()
        self._set_content_visible(False)

    def set_empty(self, message: str | None = None) -> None:
        self._status.setText(message or S.MARKET_CTX_EMPTY)
        self._status.show()
        self._set_content_visible(False)

    def set_error(self, detail: str) -> None:
        self._status.setText(S.MARKET_CTX_ERROR.format(detail=detail or "error"))
        self._status.show()
        self._set_content_visible(False)

    def set_context(self, raw: dict[str, Any] | None) -> None:
        if not isinstance(raw, dict) or not raw.get("ok"):
            err = str((raw or {}).get("error") or "") if isinstance(raw, dict) else ""
            if err:
                self.set_error(err)
            else:
                self.set_empty()
            return
        self._status.hide()
        self._gauge.set_data(raw)
        self._ladder.set_data(raw)
        self._risk_bars.set_data(raw)
        self._meters.set_data(raw)
        self._signal_txt.setText(signal_line(raw))
        # Compact levels: nearest + confluence only under the ladder
        lvl = levels_lines(raw)
        compact = [line for line in lvl if line.startswith("Nearest") or "Confluence" in line]
        self._levels_txt.setText("\n".join(compact) or "—")
        self._risk_txt.setText(risk_line(raw))
        self._structure_txt.setText("\n".join(structure_lines(raw)[:4]) or "—")
        self._set_content_visible(True)

    def set_expanded(self, expanded: bool) -> None:
        self._section.set_expanded(expanded)

    def _set_content_visible(self, visible: bool) -> None:
        self._row.setVisible(visible)
