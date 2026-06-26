"""Kraken read-only portfolio adapter (S13) — generic-backed (S14)."""

from __future__ import annotations

from typing import Any

from trendalgo.exchanges.adapters.generic import GenericCcxtPortfolioAdapter
from trendalgo.exchanges.registry import get_entry
from trendalgo.portfolio.db import PortfolioStore


class KrakenAdapter(GenericCcxtPortfolioAdapter):
    exchange_id = "kraken"

    def __init__(self) -> None:
        super().__init__(get_entry("kraken"))


def sync_kraken_balances(store: PortfolioStore, *, dry_run: bool = True) -> dict[str, Any]:
    """Backward-compatible entry point for Kraken portfolio sync."""
    return KrakenAdapter().sync_balances(store, dry_run=dry_run)
