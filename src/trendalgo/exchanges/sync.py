"""Registry-driven portfolio sync orchestration."""

from __future__ import annotations

from typing import Any

from trendalgo.exchanges.adapters.generic import GenericCcxtPortfolioAdapter
from trendalgo.exchanges.registry import get_entry
from trendalgo.exchanges.scheduler import sync_portfolio_staggered
from trendalgo.portfolio.db import PortfolioStore


def get_portfolio_adapter(exchange_id: str) -> GenericCcxtPortfolioAdapter:
    return GenericCcxtPortfolioAdapter(get_entry(exchange_id))


def sync_all_exchanges(store: PortfolioStore, *, dry_run: bool = True) -> dict[str, Any]:
    """Sync all registry-enabled portfolio exchanges with staggered delays (CM-6)."""
    return sync_portfolio_staggered(store, dry_run=dry_run)
