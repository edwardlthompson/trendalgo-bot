"""Competition-inspired Dashboard modules (risk, market, activity, …)."""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from trendalgo.device import strings as S
from trendalgo.device.portfolio_categories import cash_drag_pct, concentration_top_pct
from trendalgo.device.portfolio_model import PortfolioOverview
from trendalgo.device.portfolio_module_catalog import title_for
from trendalgo.device.views.portfolio_hero import money, signed_money


class ExtraModule(QWidget):
    """Generic body for catalog modules with light data binding."""

    def __init__(self, module_id: str) -> None:
        super().__init__()
        self._module_id = module_id
        self._title = QLabel(title_for(module_id))
        self._title.setObjectName("hint")
        self._body = QLabel(S.PORTFOLIO_MODULE_EMPTY_HINT)
        self._body.setWordWrap(True)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self._title)
        lay.addWidget(self._body, 1)

    def set_overview(self, overview: PortfolioOverview | None, *, range_key: str) -> None:
        del range_key
        mid = self._module_id
        if overview is None:
            self._body.setText(S.PORTFOLIO_MODULE_EMPTY_HINT)
            return
        if mid == "drawdown":
            self._body.setText(f"Max drawdown: {overview.max_drawdown_pct:.2%}")
        elif mid == "risk_metrics":
            self._body.setText(
                f"Health {overview.health} · Daily {overview.daily_pnl_pct:+.2%} · "
                f"DD {overview.max_drawdown_pct:.2%}"
            )
        elif mid == "concentration":
            self._body.setText(f"Top holding: {concentration_top_pct(overview.holdings, 1):.1f}%")
        elif mid == "cash_drag":
            self._body.setText(f"Cash / stables: {cash_drag_pct(overview.holdings):.1f}%")
        elif mid == "accounts_strip":
            parts = [
                f"{a.get('name') or a.get('id')}: {money(a.get('total_usd'))}"
                for a in overview.accounts[:8]
            ]
            self._body.setText(" · ".join(parts) or S.PORTFOLIO_MODULE_EMPTY)
        elif mid == "best_worst_days":
            self._body.setText(_best_worst(overview))
        elif mid == "rebalance_drift":
            rows = overview.rebalance[:6]
            self._body.setText(
                "\n".join(
                    f"{r.get('asset')}: {r.get('delta_pct', r.get('suggestion', '—'))}"
                    for r in rows
                )
                or S.PORTFOLIO_MODULE_EMPTY_HINT
            )
        elif mid in {
            "market_overview",
            "fear_greed",
            "watchlist",
            "recent_activity",
            "income_yield",
            "trade_stats",
            "exposure_by_venue",
            "goals_progress",
            "tax_lots_summary",
        }:
            self._body.setText(S.PORTFOLIO_MODULE_EMPTY_HINT)
        else:
            self._body.setText(S.PORTFOLIO_MODULE_EMPTY_HINT)


def _best_worst(overview: PortfolioOverview) -> str:
    equity = overview.equity
    if len(equity) < 2:
        return S.PORTFOLIO_NO_HISTORY
    deltas = []
    prev = None
    for e in equity:
        val = float(e.get("total_usd") or 0)
        if prev is not None:
            deltas.append((str(e.get("date") or e.get("captured_at") or ""), val - prev))
        prev = val
    if not deltas:
        return S.PORTFOLIO_NO_HISTORY
    best = max(deltas, key=lambda t: t[1])
    worst = min(deltas, key=lambda t: t[1])
    return f"Best {best[0]}: {signed_money(best[1])} · Worst {worst[0]}: {signed_money(worst[1])}"


class StatRow(QWidget):
    def __init__(self, labels: tuple[str, ...]) -> None:
        super().__init__()
        row = QHBoxLayout(self)
        self._stats = []
        for label in labels:
            box = QVBoxLayout()
            t = QLabel(label)
            t.setObjectName("hint")
            v = QLabel("—")
            v.setObjectName("sectionTitle")
            box.addWidget(t)
            box.addWidget(v)
            row.addLayout(box, 1)
            self._stats.append(v)
