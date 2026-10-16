"""Host → device portfolio sync."""

from __future__ import annotations

from pathlib import Path

from trendalgo.device.portfolio_sync import apply_host_portfolio, host_portfolio_payload
from trendalgo.portfolio.db import HoldingRow, PortfolioStore


def test_round_trip_host_portfolio_payload(tmp_path: Path) -> None:
    host = tmp_path / "host" / "portfolio.db"
    device = tmp_path / "device" / "portfolio.db"
    store = PortfolioStore(host, create=True)
    account = store.get_or_create_account("kraken", "default")
    store.insert_snapshot(
        account,
        1500.0,
        [HoldingRow("BTC", 0.01, 100_000.0, 1000.0, 900.0)],
        source="test",
    )
    store.upsert_daily_aggregate(account, "2026-10-01", 1400.0, 10.0, 0.0, 10.0)
    payload = host_portfolio_payload(host)
    assert payload is not None
    assert payload["snapshot"]["total_usd"] == 1500.0
    assert apply_host_portfolio(device, payload)
    local = PortfolioStore(device, create=False)
    accounts = local.list_accounts()
    assert accounts
    snap = local.latest_snapshot(int(accounts[0]["id"]))
    assert snap is not None
    assert float(snap["total_usd"]) == 1500.0
