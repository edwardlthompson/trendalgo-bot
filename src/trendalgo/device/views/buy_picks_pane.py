"""Collapsible Buy picks band for Scanner Qualified (Market Context + top TA)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from trendalgo.device import strings as S
from trendalgo.device.buy_picks import rank_buy_picks
from trendalgo.device.views.buy_picks_gfx import ScoreSpectrum
from trendalgo.device.views.collapsible_section import CollapsibleSection

_PAIR_W = 140
_HEADERS: tuple[tuple[str, str], ...] = (
    (S.BUY_PICKS_COL_PAIR, S.BUY_PICKS_TIP_PAIR),
    (S.BUY_PICKS_COL_BIAS, S.BUY_PICKS_TIP_BIAS),
    (S.BUY_PICKS_COL_SIGNAL, S.BUY_PICKS_TIP_SIGNAL),
    (S.BUY_PICKS_COL_CONF, S.BUY_PICKS_TIP_CONF),
    (S.BUY_PICKS_COL_SCORE, S.BUY_PICKS_TIP_SCORE),
    (S.BUY_PICKS_COL_NEAR, S.BUY_PICKS_TIP_NEAR),
    (S.BUY_PICKS_COL_RR, S.BUY_PICKS_TIP_RR),
    (S.BUY_PICKS_COL_LEVELS, S.BUY_PICKS_TIP_LEVELS),
    (S.BUY_PICKS_COL_TA, S.BUY_PICKS_TIP_TA),
)


class BuyPicksPane(QFrame):
    """Ranked Buy recommendations above the Qualified table."""

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
        self.setAccessibleName(S.BUY_PICKS_TITLE)
        self._on_collapse = on_collapse
        self._section = CollapsibleSection(S.BUY_PICKS_TITLE, expanded=expanded)
        self._subtitle = QLabel(S.BUY_PICKS_SUBTITLE)
        self._subtitle.setObjectName("hint")
        self._subtitle.setWordWrap(True)
        self._empty = QLabel(S.BUY_PICKS_EMPTY)
        self._empty.setObjectName("hint")
        self._empty.setWordWrap(True)
        self._list = QFrame()
        self._list.setObjectName("marketCtxModule")
        self._list_lay = QGridLayout(self._list)
        self._list_lay.setContentsMargins(8, 6, 8, 6)
        self._list_lay.setHorizontalSpacing(10)
        self._list_lay.setVerticalSpacing(6)
        self._list_lay.setColumnMinimumWidth(0, _PAIR_W)
        self._list_lay.setColumnStretch(0, 0)
        self._list_lay.setColumnStretch(1, 3)
        for col in range(2, 8):
            self._list_lay.setColumnStretch(col, 0)
        self._list_lay.setColumnStretch(8, 1)

        body = self._section.body_layout()
        body.addWidget(self._subtitle)
        body.addWidget(self._empty)
        body.addWidget(self._list)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self._section)
        self._section.toggled.connect(self._on_toggled)
        self.set_picks([])

    def _on_toggled(self, expanded: bool) -> None:
        self.collapsed_changed.emit(not expanded)
        if self._on_collapse is not None:
            self._on_collapse(not expanded)

    def set_expanded(self, expanded: bool) -> None:
        self._section.set_expanded(expanded)

    def set_from_coins(self, coins: list[dict[str, Any]]) -> None:
        self.set_picks(rank_buy_picks(coins))

    def set_picks(self, picks: list[dict[str, Any]]) -> None:
        while self._list_lay.count():
            item = self._list_lay.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        if not picks:
            self._subtitle.setText(S.BUY_PICKS_SUBTITLE)
            self._empty.show()
            self._list.hide()
            return
        self._subtitle.setText(S.BUY_PICKS_SUBTITLE)
        self._empty.hide()
        self._list.show()
        _add_headers(self._list_lay)
        for i, pick in enumerate(picks):
            _add_pick_row(self._list_lay, i + 1, pick)


def _add_headers(grid: QGridLayout) -> None:
    for col, (label, tip) in enumerate(_HEADERS):
        hdr = QLabel(label)
        hdr.setObjectName("hint")
        hdr.setToolTip(tip)
        hdr.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        grid.addWidget(hdr, 0, col)


def _cell(text: str, *, align: Qt.AlignmentFlag | None = None) -> QLabel:
    lab = QLabel(text)
    lab.setObjectName("hint")
    lab.setWordWrap(False)
    lab.setAlignment((align or Qt.AlignmentFlag.AlignLeft) | Qt.AlignmentFlag.AlignVCenter)
    return lab


def _add_pick_row(grid: QGridLayout, row: int, pick: dict[str, Any]) -> None:
    pair_txt = str(pick.get("pair") or pick.get("symbol") or "—")
    pair = QLabel(pair_txt)
    pair.setObjectName("sectionTitle")
    pair.setMinimumWidth(_PAIR_W)
    pair.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred)
    pair.setToolTip(pair_txt)

    spectrum = ScoreSpectrum()
    spectrum.setMinimumWidth(120)
    spectrum.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    try:
        spectrum.set_score(float(pick.get("score") or 0.0))
    except (TypeError, ValueError):
        spectrum.set_score(0.0)

    rr = pick.get("rr_r1")
    try:
        rr_s = f"{float(rr):.2f}" if rr is not None else S.BUY_PICKS_TA_NONE
    except (TypeError, ValueError):
        rr_s = S.BUY_PICKS_TA_NONE

    score_s = f"{float(pick.get('score') or 0):.2f}"
    conf_s = str(int(float(pick.get("confidence") or 0)))
    ta = _ta_text(pick)

    grid.addWidget(pair, row, 0)
    grid.addWidget(spectrum, row, 1)
    grid.addWidget(_cell(str(pick.get("signal") or "Neutral")), row, 2)
    grid.addWidget(_cell(conf_s), row, 3)
    grid.addWidget(_cell(score_s), row, 4)
    grid.addWidget(_cell(str(pick.get("nearest_sr") or "—")), row, 5)
    grid.addWidget(_cell(rr_s), row, 6)
    grid.addWidget(_cell(str(int(pick.get("confluence") or 0))), row, 7)
    grid.addWidget(_cell(ta), row, 8)


def _ta_text(pick: dict[str, Any]) -> str:
    best = pick.get("bot_best_net_pct")
    label = str(pick.get("bot_best_label") or "").strip()
    if best is None:
        return S.BUY_PICKS_TA_NONE
    ta = f"+{float(best):.1f}%"
    return f"{ta} ({label})" if label else ta
