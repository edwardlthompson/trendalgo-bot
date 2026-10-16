"""Column filter strip: health, uniformity, vol Δ, 24h vol, chart-dist 7d/30d."""

from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QWidget

from trendalgo.device import strings as S

_CHART_OPTS = (("", "All"), ("5", "Ex ≥5%"), ("10", "Ex ≥10%"), ("15", "Ex ≥15%"))
_HEALTH_OPTS = (("", "All"), ("60", "≥ 60"), ("65", "≥ 65"), ("70", "≥ 70"))
_UNIT_OPTS = (
    ("", "All"),
    ("20", "≥ 20"),
    ("30", "≥ 30"),
    ("40", "≥ 40"),
    ("50", "≥ 50"),
    ("60", "≥ 60"),
)
_VOL_ACCEL_OPTS = (("", "All"), ("pos", "Positive"), ("25", "≥ 25%"), ("50", "≥ 50%"))
_VOL24_OPTS = (
    ("", "All"),
    ("100000", "≥ $100k"),
    ("500000", "≥ $500k"),
    ("1000000", "≥ $1M"),
    ("10000000", "≥ $10M"),
)


class ScannerColumnFilters(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.chart_dist_7d = self._combo(_CHART_OPTS)
        self.chart_dist_30d = self._combo(_CHART_OPTS)
        self.health_min = self._combo(_HEALTH_OPTS)
        self.uniformity_min = self._combo(_UNIT_OPTS)
        self.vol_accel = self._combo(_VOL_ACCEL_OPTS)
        self.vol24_min = self._combo(_VOL24_OPTS)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        for label, widget in (
            (S.SCANNER_FILTER_CHART_7D, self.chart_dist_7d),
            (S.SCANNER_FILTER_CHART_30D, self.chart_dist_30d),
            (S.SCANNER_FILTER_HEALTH, self.health_min),
            (S.SCANNER_FILTER_UNIT_MIN, self.uniformity_min),
            (S.SCANNER_FILTER_VOL_ACCEL, self.vol_accel),
            (S.SCANNER_FILTER_VOL24, self.vol24_min),
        ):
            row.addWidget(QLabel(label))
            row.addWidget(widget)
        row.addStretch(1)

    def load(self, saved: dict[str, Any]) -> None:
        self._set(self.chart_dist_7d, saved.get("chart_dist_max_7d"))
        self._set(self.chart_dist_30d, saved.get("chart_dist_max_30d"))
        self._set(self.health_min, saved.get("health_min"))
        self._set(self.uniformity_min, saved.get("uniformity_min"))
        self._set(self.vol_accel, saved.get("vol_accel_filter"))
        self._set(self.vol24_min, saved.get("vol24_min"))

    def dump(self) -> dict[str, Any]:
        return {
            "chart_dist_max_7d": self._val(self.chart_dist_7d),
            "chart_dist_max_30d": self._val(self.chart_dist_30d),
            "health_min": self._val(self.health_min),
            "uniformity_min": self._val(self.uniformity_min),
            "vol_accel_filter": self._val(self.vol_accel),
            "vol24_min": self._val(self.vol24_min),
        }

    @staticmethod
    def _combo(options: tuple[tuple[str, str], ...]) -> QComboBox:
        box = QComboBox()
        for value, label in options:
            box.addItem(label, value)
        return box

    @staticmethod
    def _set(box: QComboBox, raw: object) -> None:
        text = "" if raw is None else str(raw)
        index = box.findData(text)
        box.setCurrentIndex(index if index >= 0 else 0)

    @staticmethod
    def _val(box: QComboBox) -> str:
        data = box.currentData()
        return str(data) if data is not None else ""
