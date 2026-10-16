"""KPI summary cards for the Opportunity scanner."""

from __future__ import annotations

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout

from trendalgo.device import strings as S


class ScannerChips(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("kpiStrip")
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        self._qualified = _KpiCard(S.SCANNER_CHIP_QUALIFIED)
        self._coinbase = _KpiCard(S.SCANNER_CHIP_COINBASE)
        self._kraken = _KpiCard(S.SCANNER_CHIP_KRAKEN)
        for card in (self._qualified, self._coinbase, self._kraken):
            row.addWidget(card, 1)
        self.set_counts(0, 0, 0)

    def set_counts(self, qualified: int, coinbase: int, kraken: int) -> None:
        self._qualified.set_value(qualified)
        self._coinbase.set_value(coinbase)
        self._kraken.set_value(kraken)


class _KpiCard(QFrame):
    def __init__(self, title: str) -> None:
        super().__init__()
        self.setObjectName("kpiCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        self._title = QLabel(title.upper())
        self._title.setObjectName("kpiTitle")
        self._value = QLabel("0")
        self._value.setObjectName("kpiValue")
        layout.addWidget(self._title)
        layout.addWidget(self._value)

    def set_value(self, n: int) -> None:
        self._value.setText(S.SCANNER_CHIP_COUNT.format(n=n))
