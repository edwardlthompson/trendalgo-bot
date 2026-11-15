"""Alpaca read-only positions + equity sync (TF-P1) — paper-first, dry-run default."""

from __future__ import annotations

import os
from typing import Any

from trendalgo.brokers.registry import BrokerEntry, load_broker_registry
from trendalgo.portfolio.db import HoldingRow, PortfolioStore

_DRY_HOLDINGS: tuple[HoldingRow, ...] = (
    HoldingRow(
        asset="USD", quantity=10_000.0, price_usd=1.0, value_usd=10_000.0, cost_basis_usd=10_000.0
    ),
    HoldingRow(
        asset="AAPL", quantity=10.0, price_usd=190.0, value_usd=1_900.0, cost_basis_usd=1_800.0
    ),
    HoldingRow(
        asset="SPY", quantity=5.0, price_usd=520.0, value_usd=2_600.0, cost_basis_usd=2_500.0
    ),
)


class AlpacaPortfolioAdapter:
    """Read-only TradFi sync for the Alpaca paper broker entry."""

    broker_id = "alpaca"

    def __init__(self, entry: BrokerEntry | None = None) -> None:
        resolved = entry or load_broker_registry().by_id(self.broker_id)
        if resolved is None:
            raise KeyError("alpaca broker not in registry")
        self.entry = resolved

    def has_credentials(self) -> bool:
        key = os.environ.get(self.entry.env_key, "").strip()
        secret = os.environ.get(self.entry.env_secret, "").strip()
        return bool(key and secret)

    def sync_balances(self, store: PortfolioStore, *, dry_run: bool = True) -> dict[str, Any]:
        account_id = store.get_or_create_account(self.broker_id, "paper")
        store.set_account_meta(account_id, "tradfi")
        if dry_run or not self.has_credentials():
            holdings = list(_DRY_HOLDINGS)
            total = sum(h.value_usd for h in holdings)
            snap_id = store.insert_snapshot(
                account_id, total, holdings, source=f"dry-run-{self.broker_id}"
            )
            return {
                "account_id": account_id,
                "snapshot_id": snap_id,
                "total_usd": total,
                "holdings": len(holdings),
                "equity_usd": total,
                "mode": "dry-run",
                "broker": self.broker_id,
                "positions": [
                    {"symbol": h.asset, "qty": h.quantity, "market_value": h.value_usd}
                    for h in holdings
                    if h.asset != "USD"
                ],
            }
        # Live read path reserved for alpaca-py when keys are present (no SDK on CI path).
        raise RuntimeError(
            "Alpaca live portfolio sync requires alpaca-py + keys; use dry_run=True locally"
        )


def sync_alpaca_portfolio(store: PortfolioStore, *, dry_run: bool = True) -> dict[str, Any]:
    return AlpacaPortfolioAdapter().sync_balances(store, dry_run=dry_run)
