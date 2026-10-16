"""Advanced portfolio panels: accounts, rebalance, goals, arbitrage preview."""

from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from trendalgo.device import strings as S
from trendalgo.device.portfolio_model import PortfolioOverview
from trendalgo.device.views.widgets import EmptyState, fill_table, read_only_table, section_title
from trendalgo.portfolio.arbitrage import detect_arbitrage_opportunities
from trendalgo.portfolio.db import PortfolioStore
from trendalgo.portfolio.goals import goal_progress


class PortfolioAdvancedPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._accounts = read_only_table(S.PORTFOLIO_ACCOUNT_HEADERS, S.PORTFOLIO_ACCOUNTS)
        self._accounts_empty = EmptyState(
            S.PORTFOLIO_ACCOUNTS_EMPTY, S.PORTFOLIO_ACCOUNTS_EMPTY_BODY
        )
        self._rebalance = read_only_table(S.PORTFOLIO_REBALANCE_HEADERS, S.PORTFOLIO_REBALANCE)
        self._rebalance_empty = EmptyState(
            S.PORTFOLIO_REBALANCE_EMPTY, S.PORTFOLIO_REBALANCE_EMPTY_BODY
        )
        self._goals = QLabel(S.PORTFOLIO_GOALS_NONE)
        self._goals.setObjectName("hint")
        self._goals.setWordWrap(True)
        self._arb = read_only_table(S.PORTFOLIO_ARB_HEADERS, S.PORTFOLIO_ARB)
        self._arb_empty = EmptyState(S.PORTFOLIO_ARB_EMPTY, S.PORTFOLIO_ARB_EMPTY_BODY)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(section_title(S.PORTFOLIO_ACCOUNTS))
        layout.addWidget(self._accounts_empty)
        layout.addWidget(self._accounts)
        layout.addWidget(section_title(S.PORTFOLIO_REBALANCE))
        layout.addWidget(self._rebalance_empty)
        layout.addWidget(self._rebalance)
        layout.addWidget(section_title(S.PORTFOLIO_GOALS))
        layout.addWidget(self._goals)
        layout.addWidget(section_title(S.PORTFOLIO_ARB))
        layout.addWidget(self._arb_empty)
        layout.addWidget(self._arb)

    def set_overview(self, overview: PortfolioOverview) -> None:
        accounts = list(overview.accounts)
        fill_table(
            self._accounts,
            [(str(a.get("exchange") or ""), str(a.get("label") or "")) for a in accounts],
        )
        self._accounts.setVisible(bool(accounts))
        self._accounts_empty.setVisible(not accounts)

        reb = list(overview.rebalance)
        fill_table(
            self._rebalance,
            [
                (
                    str(r.get("asset") or ""),
                    str(r.get("action") or ""),
                    f"{float(r.get('delta_pct') or 0) * 100:.1f}%",
                    f"${float(r.get('delta_usd') or 0):+,.2f}",
                )
                for r in reb
            ],
        )
        self._rebalance.setVisible(bool(reb))
        self._rebalance_empty.setVisible(not reb)

        self._goals.setText(_goal_text(overview))

        arb_rows = _arbitrage_rows()
        fill_table(
            self._arb,
            [
                (
                    str(r.get("pair") or ""),
                    str(r.get("buy_exchange") or ""),
                    str(r.get("sell_exchange") or ""),
                    f"{float(r.get('spread_pct') or 0) * 100:.2f}%",
                )
                for r in arb_rows
            ],
        )
        self._arb.setVisible(bool(arb_rows))
        self._arb_empty.setVisible(not arb_rows)


def _goal_text(overview: PortfolioOverview) -> str:
    try:
        store = PortfolioStore(overview.path, create=False)
        goal = store.get_performance_goal()
    except Exception:
        return S.PORTFOLIO_GOALS_NONE
    if not goal or not float(goal.get("target_net_worth_usd") or 0):
        return S.PORTFOLIO_GOALS_NONE
    progress = goal_progress(
        overview.net_worth_usd,
        goal,
        max_drawdown_pct=overview.max_drawdown_pct,
    )
    label = str(goal.get("label") or "Goal")
    pct = float(progress.get("progress_pct") or 0) * 100
    return S.PORTFOLIO_GOALS_PROGRESS.format(label=label, pct=f"{pct:.0f}")


def _arbitrage_rows() -> list[dict[str, Any]]:
    try:
        payload = detect_arbitrage_opportunities(dry_run=True)
    except Exception:
        return []
    rows = payload.get("alerts") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        return []
    return [r for r in rows if isinstance(r, dict)][:8]
