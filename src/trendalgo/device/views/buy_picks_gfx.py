"""Compact Sell→Buy spectrum for Market Context top-10 rows."""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from trendalgo.device.theme import active_mode
from trendalgo.device.theme_css import colors_for
from trendalgo.device.views.market_context_gfx import (
    BUY_THRESHOLD,
    score_to_frac,
)

_H = 18


class ScoreSpectrum(QWidget):
    """Horizontal Sell | Neutral | Buy track with vertical tick at consensus score."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(_H)
        self.setMinimumWidth(120)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._score = 0.0

    def set_score(self, score: float) -> None:
        try:
            self._score = float(score)
        except (TypeError, ValueError):
            self._score = 0.0
        self.update()

    def paintEvent(self, _event: object) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = colors_for(active_mode())
        track = QRectF(2, 4, self.width() - 4, self.height() - 8)
        sell_end = score_to_frac(-BUY_THRESHOLD)
        buy_start = score_to_frac(BUY_THRESHOLD)
        zones = (
            (0.0, sell_end, c.get("gainDown", c["error"])),
            (sell_end, buy_start, c["secondary"]),
            (buy_start, 1.0, c.get("gainUp", c["primary"])),
        )
        for lo, hi, color in zones:
            x = track.x() + lo * track.width()
            w = max(1.0, (hi - lo) * track.width())
            p.setBrush(QColor(color))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(QRectF(x, track.y(), w, track.height()), 3, 3)
        frac = score_to_frac(self._score)
        tx = track.x() + frac * track.width()
        p.setPen(QPen(QColor(c["onSurface"]), 2))
        p.drawLine(int(tx), int(track.y() - 2), int(tx), int(track.bottom() + 2))


def spectrum_tick_x(width: float, score: float, *, margin: float = 2.0) -> float:
    """Test helper: tick x for a given widget width."""
    track_w = max(1.0, width - 2 * margin)
    return margin + score_to_frac(score) * track_w
