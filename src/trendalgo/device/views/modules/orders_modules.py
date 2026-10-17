"""Open orders/positions and top gainers/losers."""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from trendalgo.device import strings as S
from trendalgo.device.portfolio_model import PortfolioOverview
from trendalgo.device.views.portfolio_hero import money, signed_money


class OpenOrdersModule(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._label = QLabel(S.PORTFOLIO_MODULE_EMPTY)
        self._label.setObjectName("hint")
        self._label.setWordWrap(True)
        self._hint = QLabel(S.PORTFOLIO_MODULE_EMPTY_HINT)
        self._hint.setObjectName("hint")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addStretch(1)
        lay.addWidget(self._label)
        lay.addWidget(self._hint)
        lay.addStretch(1)

    def set_overview(self, overview: PortfolioOverview | None, *, range_key: str) -> None:
        del overview, range_key
        self._label.setText(S.PORTFOLIO_MODULE_EMPTY)


class OpenPositionsModule(OpenOrdersModule):
    def set_overview(self, overview: PortfolioOverview | None, *, range_key: str) -> None:
        del range_key
        if overview is None or not overview.holdings:
            self._label.setText(S.PORTFOLIO_MODULE_EMPTY)
            return
        lines = [
            f"{h.get('asset')}: {money(h.get('value_usd'))}"
            for h in overview.holdings[:12]
            if h.get("asset")
        ]
        self._label.setText("\n".join(lines) or S.PORTFOLIO_MODULE_EMPTY)
        self._hint.setText("")


class TopGainersModule(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._label = QLabel("—")
        self._label.setWordWrap(True)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self._label)

    def set_overview(self, overview: PortfolioOverview | None, *, range_key: str) -> None:
        del range_key
        self._label.setText(_rank(overview, reverse=True))


class TopLosersModule(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._label = QLabel("—")
        self._label.setWordWrap(True)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self._label)

    def set_overview(self, overview: PortfolioOverview | None, *, range_key: str) -> None:
        del range_key
        self._label.setText(_rank(overview, reverse=False))


def _rank(overview: PortfolioOverview | None, *, reverse: bool) -> str:
    if overview is None:
        return S.PORTFOLIO_MODULE_EMPTY
    rows = []
    for h in overview.holdings:
        change = h.get("change_24h_pct")
        if isinstance(change, (int, float)):
            rows.append((str(h.get("asset") or "?"), float(change), float(h.get("value_usd") or 0)))
        else:
            pnl = float(h.get("unrealized_pnl_usd") or 0)
            rows.append((str(h.get("asset") or "?"), pnl, float(h.get("value_usd") or 0)))
    rows.sort(key=lambda t: t[1], reverse=reverse)
    if not rows:
        return S.PORTFOLIO_MODULE_EMPTY
    return "\n".join(
        f"{i + 1}. {name}  {signed_money(chg) if abs(chg) > 1 else f'{chg:+.2f}%'}  {money(val)}"
        for i, (name, chg, val) in enumerate(rows[:5])
    )
