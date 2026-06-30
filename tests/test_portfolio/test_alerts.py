"""Portfolio alert tests."""

from __future__ import annotations

from pathlib import Path

from trendalgo.portfolio.alerts import check_portfolio_alerts
from trendalgo.portfolio.db import PortfolioStore


def test_check_portfolio_alerts_drop_and_allocation(tmp_path: Path) -> None:
    store = PortfolioStore(tmp_path / "portfolio.db")
    account_id = store.get_or_create_account("kraken", "default")
    overview = {
        "daily_pnl_pct": -0.08,
        "allocation": [{"asset": "BTC", "pct": 0.85}],
    }
    messages = check_portfolio_alerts(store, account_id, overview)
    assert len(messages) == 2
    notes = store.list_notifications(limit=5)
    assert len(notes) == 2
