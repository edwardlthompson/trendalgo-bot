"""Wrappers for existing timeline and advanced panels."""

from __future__ import annotations

from PySide6.QtWidgets import QVBoxLayout, QWidget

from trendalgo.device.context import DeviceContext
from trendalgo.device.portfolio_model import PortfolioOverview
from trendalgo.device.views.portfolio_advanced_panel import PortfolioAdvancedPanel
from trendalgo.device.views.portfolio_timeline import PortfolioTimeline


class TimelineModule(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._timeline = PortfolioTimeline(lambda _d: None)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self._timeline)

    def set_overview(self, overview: PortfolioOverview | None, *, range_key: str) -> None:
        del range_key
        if overview is None:
            self._timeline.set_dates([])
            return
        self._timeline.set_dates(list(overview.snapshot_dates))


class AdvancedModule(QWidget):
    def __init__(self, ctx: DeviceContext) -> None:
        super().__init__()
        del ctx
        self._panel = PortfolioAdvancedPanel()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self._panel)

    def set_overview(self, overview: PortfolioOverview | None, *, range_key: str) -> None:
        del range_key
        if overview is None:
            return
        self._panel.set_overview(overview)
