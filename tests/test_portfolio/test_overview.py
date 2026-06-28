from pathlib import Path

from trendalgo.api.state import default_state
from trendalgo.portfolio.db import PortfolioStore
from trendalgo.portfolio.overview import build_portfolio_overview, heatmap_rows
from trendalgo.portfolio.sync import sync_kraken_balances


def test_build_overview(tmp_path: Path) -> None:
    state = default_state()
    state.portfolio_store = PortfolioStore(tmp_path / "portfolio.db")
    sync_kraken_balances(state.portfolio_store, dry_run=True)
    overview = build_portfolio_overview(state)
    assert overview["net_worth_usd"] > 40_000.0
    assert overview["holdings"]
    assert len(overview["equity_curve"]) >= 300
    assert overview["performance_ranges"] == ["1y", "6m", "3m", "1m", "14d", "7d", "24h"]
    assert overview["health_score"] >= 0
    rows = heatmap_rows(overview["holdings"])
    assert rows
