"""Multi-chain venue sync orchestration (S22, CM-6 pattern)."""

from __future__ import annotations

import os
import time
from typing import Any

from trendalgo.billing.venue_attribution import attribution_by_venue
from trendalgo.portfolio.db import PortfolioStore
from trendalgo.venues.registry import VenueEntry, list_wallet_venues, load_venue_registry
from trendalgo.venues.wallet_sync import sync_wallet


def stagger_delay_sec(entry: VenueEntry) -> float:
    override = os.environ.get("TRENDALGO_VENUE_SYNC_STAGGER_SEC")
    if override is not None:
        return float(override)
    if entry.sync_interval_sec is not None:
        return float(entry.sync_interval_sec)
    return float(load_venue_registry().default_sync_interval_sec)


def _address_for_venue(address: str, entry: VenueEntry) -> str | None:
    addr = address.strip()
    if entry.chain_type == "evm" and addr.startswith("0x"):
        return addr
    if entry.chain_type == "solana" and not addr.startswith("0x"):
        return addr
    return None


def sync_all_wallet_venues(
    store: PortfolioStore,
    address: str,
    *,
    dry_run: bool = True,
    include_lp: bool = True,
) -> dict[str, Any]:
    """Sync wallet balances (+ LP on EVM) across all registry wallet venues."""
    registry = load_venue_registry()
    results: dict[str, Any] = {}
    mode = "dry-run"
    venues = list_wallet_venues()
    started = time.perf_counter()

    for index, entry in enumerate(venues):
        if index > 0:
            time.sleep(stagger_delay_sec(entry))
        resolved = _address_for_venue(address, entry)
        if resolved is None:
            results[entry.id] = {
                "venue": entry.id,
                "skipped": True,
                "reason": f"address incompatible with {entry.chain_type}",
            }
            continue
        result = sync_wallet(
            store,
            resolved,
            venue_id=entry.id,
            dry_run=dry_run,
            include_lp=include_lp,
        )
        results[entry.id] = result
        if not result.get("dry_run", True):
            mode = "live"

    elapsed = time.perf_counter() - started
    sync_results = {
        k: v for k, v in results.items() if isinstance(v, dict) and not v.get("skipped")
    }
    return {
        **results,
        "registry_version": registry.version,
        "mode": mode,
        "staggered": True,
        "venue_count": len(venues),
        "synced_count": len(sync_results),
        "elapsed_sec": round(elapsed, 3),
        "attribution_by_venue": attribution_by_venue(sync_results),
    }
