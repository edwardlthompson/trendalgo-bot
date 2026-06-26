"""Read-only on-chain wallet sync — delegates to venue plugins (ADR-0011, S21)."""

from __future__ import annotations

from typing import Any

from trendalgo.portfolio.db import PortfolioStore
from trendalgo.venues.registry import get_venue, load_venue_registry
from trendalgo.venues.wallet_sync import preview_wallet, sync_wallet


def _resolve_venue(chain: str) -> str:
    venue_id = chain.strip().lower()
    entry = load_venue_registry().by_id(venue_id)
    if entry is None or not entry.wallet_read_enabled:
        raise ValueError(f"unsupported chain: {chain}")
    return venue_id


def sync_onchain_wallet(
    store: PortfolioStore,
    address: str,
    *,
    chain: str = "ethereum",
    dry_run: bool = True,
    include_lp: bool = True,
) -> dict[str, Any]:
    """Sync read-only balances (+ LP on EVM) for an on-chain wallet."""
    venue_id = _resolve_venue(chain)
    get_venue(venue_id)
    return sync_wallet(store, address, venue_id=venue_id, dry_run=dry_run, include_lp=include_lp)


def preview_onchain_wallet(
    address: str,
    *,
    chain: str = "ethereum",
    include_lp: bool = True,
) -> dict[str, Any]:
    """Preview balances and LP positions without persisting."""
    venue_id = _resolve_venue(chain)
    return preview_wallet(address, venue_id=venue_id, include_lp=include_lp)
