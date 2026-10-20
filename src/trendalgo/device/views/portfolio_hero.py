"""Portfolio hero metrics and money formatting helpers."""

from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from trendalgo.device import strings as S
from trendalgo.device.portfolio_model import PortfolioOverview


class PortfolioHero(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("panel")
        row = QHBoxLayout(self)
        self._net = _Metric(S.PORTFOLIO_NET_WORTH)
        self._daily = _Metric(S.PORTFOLIO_DAILY)
        self._total = _Metric(S.PORTFOLIO_TOTAL_PL)
        self._health = _Metric(S.PORTFOLIO_HEALTH)
        self._dd = _Metric(S.PORTFOLIO_DRAWDOWN)
        self._realized = _Metric(S.PORTFOLIO_REALIZED)
        self._unrealized = _Metric(S.PORTFOLIO_UNREALIZED)
        for widget in (
            self._net,
            self._daily,
            self._total,
            self._health,
            self._dd,
            self._realized,
            self._unrealized,
        ):
            row.addWidget(widget, 1)

    def set_overview(self, overview: PortfolioOverview) -> None:
        self._net.set_value(money(overview.net_worth_usd))
        daily = f"{signed_money(overview.daily_pnl_usd)} ({overview.daily_pnl_pct:+.2%})"
        self._daily.set_value(daily)
        self._total.set_value(signed_money(overview.total_pl_usd))
        self._health.set_value(str(overview.health))
        self._dd.set_value(f"{overview.max_drawdown_pct:.2%}")
        if overview.realized_available:
            self._realized.set_value(signed_money(overview.realized_usd))
        else:
            self._realized.set_value(S.PORTFOLIO_REALIZED_UNAVAILABLE)
        self._unrealized.set_value(signed_money(overview.unrealized_usd))


class _Metric(QWidget):
    def __init__(self, label: str) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        title = QLabel(label)
        title.setObjectName("hint")
        self._value = QLabel("—")
        self._value.setObjectName("sectionTitle")
        layout.addWidget(title)
        layout.addWidget(self._value)

    def set_value(self, text: str) -> None:
        self._value.setText(text)


def pl_lines(rows: list[dict[str, Any]]) -> str:
    parts = [
        f"{h.get('asset')}: {signed_money(h.get('unrealized_pnl_usd'))}"
        for h in rows
        if h.get("asset")
    ]
    return " · ".join(parts)


def money(raw: object) -> str:
    value = as_float(raw)
    return "—" if value is None else f"${value:,.2f}"


def signed_money(raw: object) -> str:
    value = as_float(raw)
    return "—" if value is None else f"${value:+,.2f}"


def as_float(raw: object) -> float | None:
    if isinstance(raw, bool):
        return None
    if isinstance(raw, int | float):
        return float(raw)
    if isinstance(raw, str):
        try:
            return float(raw)
        except ValueError:
            return None
    return None
