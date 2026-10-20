"""Allocation donut / bar / heatmap modules."""

from __future__ import annotations

from PySide6.QtCharts import QChart, QChartView, QPieSeries
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from trendalgo.device import strings as S
from trendalgo.device.portfolio_categories import category_totals
from trendalgo.device.portfolio_model import PortfolioOverview
from trendalgo.device.views.holdings_heatmap import HoldingsHeatmap
from trendalgo.device.views.portfolio_allocation_bar import PortfolioAllocationBar
from trendalgo.device.views.portfolio_hero import money
from trendalgo.portfolio.metrics import heatmap_rows


class CoinAllocationModule(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._series = QPieSeries()
        self._series.setHoleSize(0.45)
        chart = QChart()
        chart.addSeries(self._series)
        chart.legend().setVisible(False)
        chart.setBackgroundVisible(False)
        self._view = QChartView(chart)
        self._view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._legend = QLabel("")
        self._legend.setWordWrap(True)
        self._legend.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self._view, 3)
        lay.addWidget(self._legend, 1)

    def set_overview(self, overview: PortfolioOverview | None, *, range_key: str) -> None:
        del range_key
        self._series.clear()
        if overview is None or not overview.allocation:
            self._legend.setText(S.PORTFOLIO_MODULE_EMPTY)
            return
        lines = []
        for row in overview.allocation[:8]:
            name = str(row.get("asset") or "?")
            pct = float(row.get("pct") or row.get("allocation_pct") or 0)
            val = float(row.get("value_usd") or 0)
            slice_ = self._series.append(name, max(pct, 0.01))
            del slice_
            lines.append(f"{name}  {pct:.2f}%  {money(val)}")
        self._legend.setText("\n".join(lines))


class CategoryAllocationModule(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._series = QPieSeries()
        self._series.setHoleSize(0.5)
        chart = QChart()
        chart.addSeries(self._series)
        chart.legend().setVisible(False)
        chart.setBackgroundVisible(False)
        self._view = QChartView(chart)
        self._view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._legend = QLabel("")
        self._legend.setWordWrap(True)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self._view, 3)
        lay.addWidget(self._legend, 1)

    def set_overview(self, overview: PortfolioOverview | None, *, range_key: str) -> None:
        del range_key
        self._series.clear()
        if overview is None:
            self._legend.setText(S.PORTFOLIO_MODULE_EMPTY)
            return
        rows = category_totals(overview.holdings)
        lines = []
        for row in rows:
            value = row.get("value_usd")
            if value is None:
                lines.append(f"{row['category']}  {S.PORTFOLIO_NFT_UNTRACKED}")
                continue
            if float(value) <= 0:
                continue
            pct = float(row.get("pct") or 0.0)
            self._series.append(row["category"], max(pct, 0.01))
            lines.append(f"{row['category']}  {pct:.2f}%  {money(float(value))}")
        self._legend.setText("\n".join(lines) or S.PORTFOLIO_MODULE_EMPTY)


class AssetAllocationModule(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._bar = PortfolioAllocationBar()
        self._legend = QLabel("")
        self._legend.setObjectName("hint")
        self._legend.setWordWrap(True)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self._bar)
        lay.addWidget(self._legend)

    def set_overview(self, overview: PortfolioOverview | None, *, range_key: str) -> None:
        del range_key
        if overview is None:
            self._bar.set_allocation([])
            self._legend.setText(S.PORTFOLIO_MODULE_EMPTY)
            return
        cats = category_totals(overview.holdings)
        self._bar.set_allocation(
            [{"asset": c["category"], "pct": c["pct"], "value_usd": c["value_usd"]} for c in cats]
        )
        self._legend.setText(
            " · ".join(f"{c['category']} {money(c['value_usd'])}" for c in cats if c["value_usd"])
        )


class HeatmapModule(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._heat = HoldingsHeatmap()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self._heat)

    def set_overview(self, overview: PortfolioOverview | None, *, range_key: str) -> None:
        del range_key
        if overview is None:
            self._heat.set_rows([])
            return
        self._heat.set_rows(heatmap_rows(overview.holdings))
