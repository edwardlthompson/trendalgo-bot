"""Total Worth and PL Insights Dashboard modules."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from trendalgo.device import strings as S
from trendalgo.device.portfolio_model import PortfolioOverview
from trendalgo.device.portfolio_module_catalog import RANGE_CHIPS
from trendalgo.device.views.chip_bar import ChipBar
from trendalgo.device.views.portfolio_hero import money, signed_money
from trendalgo.device.views.sparkline import Sparkline


class TotalWorthModule(QWidget):
    def __init__(self, *, on_range: Callable[[str], None] | None = None) -> None:
        super().__init__()
        self._on_range = on_range
        eyebrow = QLabel("Total Assets")
        eyebrow.setObjectName("dashStatLabel")
        self._value = QLabel("—")
        self._value.setObjectName("dashHeroValue")
        self._delta = QLabel("")
        self._delta.setObjectName("dashMuted")
        self._chips = ChipBar(RANGE_CHIPS, on_change=self._range_changed)
        quote = QLabel(S.PORTFOLIO_QUOTE_USD)
        quote.setObjectName("badge")
        value_row = QHBoxLayout()
        value_row.setContentsMargins(0, 0, 0, 0)
        value_row.setSpacing(10)
        value_row.addWidget(self._value, 0, Qt.AlignmentFlag.AlignLeft)
        value_row.addWidget(quote, 0, Qt.AlignmentFlag.AlignVCenter)
        value_row.addStretch(1)
        left = QVBoxLayout()
        left.setContentsMargins(0, 0, 0, 0)
        left.setSpacing(4)
        left.addWidget(eyebrow)
        left.addLayout(value_row)
        left.addWidget(self._delta)
        left.addWidget(self._chips)
        left.addStretch(1)
        self._spark = Sparkline()
        self._spark.setMinimumSize(220, 72)
        self._spark.setMaximumHeight(96)
        self._spark.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        body = QHBoxLayout(self)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(16)
        body.addLayout(left, 2)
        body.addWidget(self._spark, 3, Qt.AlignmentFlag.AlignVCenter)

    def resizeEvent(self, event: object) -> None:  # noqa: N802
        from PySide6.QtGui import QResizeEvent

        if isinstance(event, QResizeEvent):
            super().resizeEvent(event)
        # ~3 grid rows of body: hide chips; narrow width: hide spark.
        self._chips.setVisible(self.height() >= 140)
        self._spark.setVisible(self.width() >= 360)

    def set_overview(self, overview: PortfolioOverview | None, *, range_key: str) -> None:
        self._chips.set_selected(_chip_key(range_key))
        if overview is None:
            self._value.setText("—")
            self._delta.setText(S.PORTFOLIO_MODULE_EMPTY)
            self._delta.setObjectName("dashMuted")
            self._spark.set_values([])
            return
        self._value.setText(money(overview.net_worth_usd))
        self._delta.setText(
            f"{signed_money(overview.daily_pnl_usd)}  ({overview.daily_pnl_pct:+.2%})"
        )
        self._delta.setObjectName("dashDeltaUp" if overview.daily_pnl_usd >= 0 else "dashDeltaDown")
        self._delta.style().unpolish(self._delta)
        self._delta.style().polish(self._delta)
        vals = [float(p.get("total_usd") or 0) for p in (overview.equity or [])]
        self._spark.set_values(vals[-120:])

    def _range_changed(self, key: str) -> None:
        if self._on_range is not None:
            self._on_range(key)


class PlInsightsModule(QWidget):
    def __init__(self) -> None:
        super().__init__()
        grid = QVBoxLayout(self)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(10)
        top = QHBoxLayout()
        top.setSpacing(12)
        bottom = QHBoxLayout()
        bottom.setSpacing(12)
        self._cost = _Stat("Total Cost")
        self._unreal = _Stat(S.PORTFOLIO_UNREALIZED)
        self._real = _Stat(S.PORTFOLIO_REALIZED)
        self._all = _Stat(S.PORTFOLIO_TOTAL_PL)
        top.addWidget(self._cost, 1)
        top.addWidget(self._unreal, 1)
        bottom.addWidget(self._real, 1)
        bottom.addWidget(self._all, 1)
        grid.addLayout(top)
        grid.addLayout(bottom)
        grid.addStretch(1)

    def set_overview(self, overview: PortfolioOverview | None, *, range_key: str) -> None:
        del range_key
        if overview is None:
            for w in (self._cost, self._unreal, self._real, self._all):
                w.set_value("—")
            return
        cost = overview.net_worth_usd - overview.unrealized_usd
        self._cost.set_value(money(cost))
        self._unreal.set_value(
            signed_money(overview.unrealized_usd), signed=overview.unrealized_usd
        )
        self._real.set_value(signed_money(overview.realized_usd), signed=overview.realized_usd)
        self._all.set_value(signed_money(overview.total_pl_usd), signed=overview.total_pl_usd)


class _Stat(QWidget):
    def __init__(self, label: str) -> None:
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)
        title = QLabel(label)
        title.setObjectName("dashStatLabel")
        self._value = QLabel("—")
        self._value.setObjectName("dashStatValue")
        lay.addWidget(title)
        lay.addWidget(self._value)

    def set_value(self, text: str, *, signed: float | None = None) -> None:
        self._value.setText(text)
        if signed is None:
            self._value.setObjectName("dashStatValue")
        elif signed >= 0:
            self._value.setObjectName("dashDeltaUp")
        else:
            self._value.setObjectName("dashDeltaDown")
        self._value.style().unpolish(self._value)
        self._value.style().polish(self._value)


def _chip_key(range_key: str) -> str:
    aliases = {"1w": "7d", "24H": "24h", "1W": "7d"}
    return aliases.get(range_key, range_key)
