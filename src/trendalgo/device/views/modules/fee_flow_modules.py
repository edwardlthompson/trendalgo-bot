"""Fees and inflows/outflows modules (empty until ledger sync)."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from trendalgo.device import strings as S
from trendalgo.device.portfolio_model import PortfolioOverview
from trendalgo.device.portfolio_module_catalog import RANGE_CHIPS
from trendalgo.device.views.chip_bar import ChipBar
from trendalgo.device.views.equity_chart import EquityChart


class TradingFeesPaidModule(QWidget):
    def __init__(self) -> None:
        super().__init__()
        row = QHBoxLayout(self)
        self._stats = [
            _Stat("Total Fees"),
            _Stat("Average"),
            _Stat("Highest Fee"),
            _Stat("Tx Count"),
        ]
        for s in self._stats:
            row.addWidget(s, 1)

    def set_overview(self, overview: PortfolioOverview | None, *, range_key: str) -> None:
        del overview, range_key
        for s in self._stats:
            s.set_value("0 USD" if "Count" not in s.label else "0")


class FundingFeesModule(TradingFeesPaidModule):
    pass


class TradingFeesMonthlyModule(QWidget):
    def __init__(self, *, on_range: Callable[[str], None] | None = None) -> None:
        super().__init__()
        self._chips = ChipBar(RANGE_CHIPS, on_change=on_range)
        self._chart = EquityChart()
        self._empty = QLabel(S.PORTFOLIO_MODULE_EMPTY_HINT)
        self._empty.setObjectName("hint")
        self._empty.setWordWrap(True)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self._chips)
        lay.addWidget(self._empty)
        lay.addWidget(self._chart, 1)
        self._chart.hide()

    def set_overview(self, overview: PortfolioOverview | None, *, range_key: str) -> None:
        del overview
        self._chips.set_selected(range_key if range_key in dict(RANGE_CHIPS) else "1y")
        self._empty.setText(S.PORTFOLIO_MODULE_EMPTY_HINT)
        self._chart.set_points([])


class InflowsOutflowsModule(QWidget):
    def __init__(self, *, on_range: Callable[[str], None] | None = None) -> None:
        super().__init__()
        self._chips = ChipBar(RANGE_CHIPS, on_change=on_range)
        self._chart = EquityChart()
        self._empty = QLabel(S.PORTFOLIO_MODULE_EMPTY_HINT)
        self._empty.setObjectName("hint")
        self._empty.setWordWrap(True)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self._chips)
        lay.addWidget(self._empty)
        lay.addWidget(self._chart, 1)

    def set_overview(self, overview: PortfolioOverview | None, *, range_key: str) -> None:
        del overview
        self._chips.set_selected(range_key if range_key in dict(RANGE_CHIPS) else "all")
        self._chart.set_points([])


class _Stat(QWidget):
    def __init__(self, label: str) -> None:
        super().__init__()
        self.label = label
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        title = QLabel(label)
        title.setObjectName("hint")
        self._value = QLabel("—")
        self._value.setObjectName("sectionTitle")
        lay.addWidget(title)
        lay.addWidget(self._value)

    def set_value(self, text: str) -> None:
        self._value.setText(text)
