"""Portfolio value / P/L chart modules."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from trendalgo.device import strings as S
from trendalgo.device.portfolio_model import PortfolioOverview, equity_for_range
from trendalgo.device.portfolio_module_catalog import RANGE_CHIPS
from trendalgo.device.views.chip_bar import ChipBar
from trendalgo.device.views.equity_chart import EquityChart
from trendalgo.device.views.portfolio_hero import money


class _ChartShell(QWidget):
    def __init__(self, *, on_range: Callable[[str], None] | None = None) -> None:
        super().__init__()
        self._on_range = on_range
        self._chips = ChipBar(RANGE_CHIPS, on_change=self._changed)
        self._chart = EquityChart()
        self._hint = QLabel("")
        self._hint.setObjectName("hint")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._chips)
        layout.addWidget(self._hint)
        layout.addWidget(self._chart, 1)

    def _changed(self, key: str) -> None:
        if self._on_range is not None:
            self._on_range(key)


class PortfolioValueModule(_ChartShell):
    def set_overview(self, overview: PortfolioOverview | None, *, range_key: str) -> None:
        self._chips.set_selected(range_key if range_key in dict(RANGE_CHIPS) else "1y")
        if overview is None:
            self._chart.set_points([])
            self._hint.setText(S.PORTFOLIO_MODULE_EMPTY)
            return
        points = _range_points(overview, range_key)
        self._chart.set_points(points)
        highs = [float(p.get("total_usd") or 0) for p in points]
        if highs:
            self._hint.setText(f"High: {money(max(highs))} · Low: {money(min(highs))}")
        else:
            self._hint.setText(S.PORTFOLIO_NO_HISTORY)


class CumulativePnlModule(_ChartShell):
    def set_overview(self, overview: PortfolioOverview | None, *, range_key: str) -> None:
        self._chips.set_selected(range_key if range_key in dict(RANGE_CHIPS) else "1y")
        if overview is None:
            self._chart.set_points([])
            return
        points = _range_points(overview, range_key)
        if not points:
            self._chart.set_points([])
            return
        base = float(points[0].get("total_usd") or 0)
        cum = [
            {
                "captured_at": p.get("captured_at"),
                "total_usd": float(p.get("total_usd") or 0) - base,
            }
            for p in points
        ]
        self._chart.set_points(cum)


class DailyPnlModule(_ChartShell):
    def set_overview(self, overview: PortfolioOverview | None, *, range_key: str) -> None:
        self._chips.set_selected(range_key if range_key in dict(RANGE_CHIPS) else "7d")
        if overview is None:
            self._chart.set_points([])
            return
        points = _range_points(overview, range_key)
        daily: list[dict[str, Any]] = []
        prev = None
        for p in points:
            val = float(p.get("total_usd") or 0)
            if prev is not None:
                daily.append({"captured_at": p.get("captured_at"), "total_usd": val - prev})
            prev = val
        self._chart.set_points(daily)


class PortfolioVsMarketModule(_ChartShell):
    def set_overview(self, overview: PortfolioOverview | None, *, range_key: str) -> None:
        self._chips.set_selected(range_key if range_key in dict(RANGE_CHIPS) else "1y")
        if overview is None:
            self._chart.set_curves([])
            return
        points = _range_points(overview, range_key)
        self._chart.set_curves(
            points,
            top10=list(overview.compare_top10) or None,
            buy_hold=list(overview.compare_buy_hold) or None,
        )


def _range_points(overview: PortfolioOverview, range_key: str) -> list[dict[str, Any]]:
    if range_key == "all":
        return [
            {"captured_at": e.get("date") or e.get("captured_at"), "total_usd": e.get("total_usd")}
            for e in overview.equity
        ]
    if range_key == "ytd":
        return _ytd(overview.equity)
    key = "7d" if range_key == "7d" else range_key
    if key not in {"1y", "6m", "3m", "1m", "14d", "7d", "24h"}:
        key = "1y"
    try:
        points = equity_for_range(overview.path, key)
        if len(points) >= 2:
            return points
    except Exception:
        pass
    return [
        {"captured_at": e.get("date") or e.get("captured_at"), "total_usd": e.get("total_usd")}
        for e in overview.equity
    ]


def _ytd(equity: list[dict[str, Any]]) -> list[dict[str, Any]]:
    from datetime import UTC, datetime

    year = datetime.now(tz=UTC).year
    out = []
    for e in equity:
        raw = str(e.get("date") or e.get("captured_at") or "")
        if raw.startswith(str(year)):
            out.append(
                {
                    "captured_at": e.get("date") or e.get("captured_at"),
                    "total_usd": e.get("total_usd"),
                }
            )
    return out
