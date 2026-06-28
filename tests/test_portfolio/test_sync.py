from pathlib import Path

from trendalgo.portfolio.db import PortfolioStore
from trendalgo.portfolio.sync import sync_kraken_balances


def test_sync_dry_run_sample(tmp_path: Path) -> None:
    store = PortfolioStore(tmp_path / "portfolio.db")
    result = sync_kraken_balances(store, dry_run=True)
    assert result["mode"] == "dry-run"
    assert result["total_usd"] > 40_000.0
    account_id = store.get_or_create_account("kraken", "default")
    snap = store.latest_snapshot(account_id)
    assert snap is not None
    assert len(snap["holdings"]) == 1
    assert snap["holdings"][0]["asset"] == "BTC"
    assert float(snap["holdings"][0]["quantity"]) == 1.0
