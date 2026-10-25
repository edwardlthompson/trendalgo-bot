"""Glanceable Market Context module graphics (QPainter)."""

from __future__ import annotations

import math
from typing import Any

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import QSizePolicy, QWidget

from trendalgo.device.theme import active_mode
from trendalgo.device.theme_css import colors_for

_GFX_H = 128
# Match indicator_consensus Buy/Sell cutoffs so gauge zones agree with the label.
BUY_THRESHOLD = 0.35


def score_to_deg(score: float) -> float:
    """Map consensus score (−2…+2) → needle degrees (Sell=180°, Neutral=90°, Buy=0°)."""
    frac = max(-1.0, min(1.0, float(score) / 2.0))
    return 90.0 - frac * 90.0


def score_to_frac(score: float) -> float:
    """Map score (−2…+2) → 0…1 left→right (Sell→Buy) for horizontal spectra."""
    return max(0.0, min(1.0, (float(score) + 2.0) / 4.0))


def zone_for_score(score: float) -> str:
    """Buy / Sell / Neutral from the same thresholds as consensus."""
    if score >= BUY_THRESHOLD:
        return "Buy"
    if score <= -BUY_THRESHOLD:
        return "Sell"
    return "Neutral"


class _GfxBase(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(_GFX_H)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)
        self._raw: dict[str, Any] = {}

    def set_data(self, raw: dict[str, Any]) -> None:
        self._raw = raw if isinstance(raw, dict) else {}
        self.update()

    def _c(self) -> dict[str, str]:
        return colors_for(active_mode())


class SignalGauge(_GfxBase):
    """Semicircle meter with needle: Sell ← Neutral → Buy."""

    def paintEvent(self, _event: object) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = self._c()
        cons = self._raw.get("consensus") if isinstance(self._raw.get("consensus"), dict) else {}
        signal = str(cons.get("signal") or "Neutral")
        score = float(cons.get("score") or 0.0)  # −2…+2
        needle_deg = score_to_deg(score)

        cx = self.width() / 2.0
        cy = self.height() - 36.0
        radius = min(self.width() * 0.42, self.height() - 48.0)
        rect = QRectF(cx - radius, cy - radius, radius * 2, radius * 2)

        # Zones from consensus thresholds (not equal thirds).
        buy_lo = score_to_deg(2.0)  # 0°
        buy_hi = score_to_deg(BUY_THRESHOLD)
        sell_lo = score_to_deg(-BUY_THRESHOLD)
        sell_hi = score_to_deg(-2.0)  # 180°
        for start, end, color_key in (
            (sell_lo, sell_hi, "gainDown"),
            (buy_hi, sell_lo, "secondary"),
            (buy_lo, buy_hi, "gainUp"),
        ):
            span = end - start
            if span <= 0:
                continue
            pen = QPen(QColor(c.get(color_key, c["outline"])))
            pen.setWidth(12)
            pen.setCapStyle(Qt.PenCapStyle.FlatCap)
            p.setPen(pen)
            p.drawArc(rect, int(start * 16), int(span * 16))

        font = QFont(p.font())
        font.setPointSize(8)
        p.setFont(font)
        for deg, label in ((180, "Sell"), (90, "N"), (0, "Buy")):
            rad = math.radians(deg)
            x1 = cx + math.cos(rad) * (radius - 8)
            y1 = cy - math.sin(rad) * (radius - 8)
            x2 = cx + math.cos(rad) * (radius + 6)
            y2 = cy - math.sin(rad) * (radius + 6)
            p.setPen(QPen(QColor(c["onSurface"]), 2))
            p.drawLine(QPointF(x1, y1), QPointF(x2, y2))
            lx = cx + math.cos(rad) * (radius + 16) - 14
            ly = cy - math.sin(rad) * (radius + 16) - 7
            p.setPen(QColor(c["onSurfaceVariant"]))
            p.drawText(QRectF(lx, ly, 32, 14), Qt.AlignmentFlag.AlignCenter, label)

        # Needle
        nrad = math.radians(needle_deg)
        tip = QPointF(cx + math.cos(nrad) * (radius - 14), cy - math.sin(nrad) * (radius - 14))
        left = QPointF(
            cx + math.cos(nrad + 1.45) * 8,
            cy - math.sin(nrad + 1.45) * 8,
        )
        right = QPointF(
            cx + math.cos(nrad - 1.45) * 8,
            cy - math.sin(nrad - 1.45) * 8,
        )
        accent = c["secondary"]
        if signal == "Buy":
            accent = c.get("gainUp", c["primary"])
        elif signal == "Sell":
            accent = c.get("gainDown", c["error"])
        p.setBrush(QColor(accent))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawPolygon(QPolygonF([tip, left, right]))
        p.setBrush(QColor(c["onSurface"]))
        p.drawEllipse(QPointF(cx, cy), 5, 5)

        font.setBold(True)
        font.setPointSize(11)
        p.setFont(font)
        p.setPen(QColor(c["onSurface"]))
        p.drawText(
            QRectF(0, self.height() - 22, self.width(), 20),
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
            signal,
        )


class LevelsLadder(_GfxBase):
    """Vertical price ladder S3…R3 with last-price marker and readable labels."""

    def paintEvent(self, _event: object) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = self._c()
        pivots = self._raw.get("pivots") if isinstance(self._raw.get("pivots"), dict) else {}
        levels = pivots.get("levels") if isinstance(pivots.get("levels"), list) else []
        last = self._raw.get("last_price")
        prices: list[tuple[str, float]] = []
        for level in levels:
            if not isinstance(level, dict):
                continue
            try:
                prices.append((str(level.get("name") or ""), float(level.get("price"))))
            except (TypeError, ValueError):
                continue
        if not prices:
            p.setPen(QColor(c["onSurfaceVariant"]))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "—")
            return
        lo = min(v for _, v in prices)
        hi = max(v for _, v in prices)
        span = max(hi - lo, 1e-9)
        x = self.width() * 0.62
        top, bot = 14.0, self.height() - 14.0
        p.setPen(QPen(QColor(c["outline"]), 2))
        p.drawLine(int(x), int(top), int(x), int(bot))
        font = QFont(p.font())
        font.setPointSize(9)
        p.setFont(font)
        for name, price in prices:
            y = bot - (price - lo) / span * (bot - top)
            color = (
                c["gainUp"]
                if name.startswith("R")
                else (c["gainDown"] if name.startswith("S") else c["secondary"])
            )
            p.setPen(QPen(QColor(color), 3))
            p.drawLine(int(x - 14), int(y), int(x + 14), int(y))
            p.setPen(QColor(c["onSurface"]))
            label = f"{name} {_short_px(price)}"
            p.drawText(QRectF(4, y - 8, x - 22, 16), Qt.AlignmentFlag.AlignVCenter, label)
        if last is not None:
            try:
                lp = float(last)
                y = bot - (lp - lo) / span * (bot - top)
                p.setBrush(QColor(c["primary"]))
                p.setPen(Qt.PenStyle.NoPen)
                p.drawEllipse(int(x - 5), int(y - 5), 10, 10)
                p.setPen(QColor(c["primary"]))
                p.drawText(
                    QRectF(x + 16, y - 8, self.width() - x - 20, 16),
                    Qt.AlignmentFlag.AlignVCenter,
                    _short_px(lp),
                )
            except (TypeError, ValueError):
                pass


class RiskBars(_GfxBase):
    """Side-by-side R:R bars for R1 / R2."""

    def paintEvent(self, _event: object) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = self._c()
        risk = self._raw.get("risk") if isinstance(self._raw.get("risk"), dict) else {}
        r1 = risk.get("rr_to_r1")
        r2 = risk.get("rr_to_r2")
        vals = [
            ("R1", float(r1) if r1 is not None else 0.0, r1 is not None),
            ("R2", float(r2) if r2 is not None else 0.0, r2 is not None),
        ]
        max_v = max((v for _, v, ok in vals if ok), default=1.0) or 1.0
        w = (self.width() - 24) / 2
        label_h = 18
        for i, (label, value, ok) in enumerate(vals):
            x = 8 + i * (w + 8)
            bar_h = (self.height() - 28 - label_h) * min(1.0, value / max(max_v, 1e-9)) if ok else 4
            y = self.height() - label_h - 8 - bar_h
            p.setBrush(QColor(c["primaryContainer"] if ok and value >= 1 else c["surfaceVariant"]))
            p.setPen(QPen(QColor(c["outline"])))
            p.drawRoundedRect(QRectF(x, y, w, bar_h), 4, 4)
            p.setPen(QColor(c["onSurface"]))
            text = f"{label} {value:.2f}" if ok else f"{label} —"
            p.drawText(
                QRectF(x, self.height() - label_h, w, label_h),
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
                text,
            )


class StructureMeters(_GfxBase):
    """Distance meters for VWAP / POC / extension."""

    def paintEvent(self, _event: object) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = self._c()
        struct = self._raw.get("structure") if isinstance(self._raw.get("structure"), dict) else {}
        rows = [
            ("VWAP", struct.get("vwap_dist_pct")),
            ("POC", _poc_dist_pct(self._raw)),
            ("Hi", struct.get("drawdown_from_high_pct")),
        ]
        h = (self.height() - 16) / 3
        font = QFont(p.font())
        font.setPointSize(9)
        p.setFont(font)
        for i, (label, raw) in enumerate(rows):
            y = 6 + i * h
            p.setPen(QColor(c["onSurfaceVariant"]))
            p.drawText(QRectF(4, y, 40, h - 4), Qt.AlignmentFlag.AlignVCenter, label)
            track = QRectF(48, y + h * 0.28, self.width() - 56, h * 0.4)
            p.setBrush(QColor(c["surfaceVariant"]))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(track, 3, 3)
            if raw is None:
                continue
            try:
                pct = float(raw)
            except (TypeError, ValueError):
                continue
            mid = track.center().x()
            frac = max(-1.0, min(1.0, pct / 5.0))
            fill_w = abs(frac) * (track.width() / 2)
            if frac >= 0:
                fill = QRectF(mid, track.y(), fill_w, track.height())
                color = c.get("gainUp", c["primary"])
            else:
                fill = QRectF(mid - fill_w, track.y(), fill_w, track.height())
                color = c.get("gainDown", c["error"])
            p.setBrush(QColor(color))
            p.drawRoundedRect(fill, 3, 3)
            p.setPen(QPen(QColor(c["outline"]), 1))
            p.drawLine(int(mid), int(track.y() - 2), int(mid), int(track.bottom() + 2))


def _poc_dist_pct(raw: dict[str, Any]) -> float | None:
    struct = raw.get("structure") if isinstance(raw.get("structure"), dict) else {}
    last = raw.get("last_price")
    poc = struct.get("poc")
    try:
        if last is None or poc is None:
            return None
        lp, pp = float(last), float(poc)
        if pp <= 0:
            return None
        return 100.0 * (lp - pp) / pp
    except (TypeError, ValueError):
        return None


def _short_px(price: float) -> str:
    if abs(price) >= 1000:
        return f"{price:,.0f}"
    if abs(price) >= 1:
        return f"{price:,.2f}"
    return f"{price:.4f}"
