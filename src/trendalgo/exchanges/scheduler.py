"""Staggered portfolio sync scheduler (CM-6 stub, S14)."""

from __future__ import annotations

import os
import time
from collections.abc import Callable
from typing import Any

from trendalgo.exchanges.adapters.generic import GenericCcxtPortfolioAdapter
from trendalgo.exchanges.registry import (
    ExchangeEntry,
    get_entry,
    list_portfolio_exchanges,
    load_registry,
)
from trendalgo.portfolio.db import PortfolioStore

SyncFn = Callable[[PortfolioStore, ExchangeEntry, bool], dict[str, Any]]


def get_portfolio_adapter(exchange_id: str) -> GenericCcxtPortfolioAdapter:
    return GenericCcxtPortfolioAdapter(get_entry(exchange_id))


def _default_sync(store: PortfolioStore, entry: ExchangeEntry, dry_run: bool) -> dict[str, Any]:
    return get_portfolio_adapter(entry.id).sync_balances(store, dry_run=dry_run)


def stagger_delay_sec(entry: ExchangeEntry, *, default: int | None = None) -> float:
    """Seconds to wait before syncing this exchange (rate-limit friendly)."""
    override = os.environ.get("TRENDALGO_SYNC_STAGGER_SEC")
    if override is not None:
        return float(override)
    if entry.sync_interval_sec is not None:
        return float(entry.sync_interval_sec)
    registry = load_registry()
    base = default if default is not None else registry.default_sync_interval_sec
    return float(base)


def sync_portfolio_staggered(
    store: PortfolioStore,
    *,
    dry_run: bool = True,
    sync_fn: SyncFn | None = None,
) -> dict[str, Any]:
    """Sync each portfolio-enabled exchange with staggered delays."""
    registry = load_registry()
    runner = sync_fn or _default_sync
    results: dict[str, Any] = {}
    mode = "dry-run"
    entries = list_portfolio_exchanges()
    started = time.perf_counter()

    for index, entry in enumerate(entries):
        if index > 0:
            time.sleep(stagger_delay_sec(entry))
        result = runner(store, entry, dry_run)
        results[entry.id] = result
        if result.get("mode") == "live":
            mode = "live"

    elapsed = time.perf_counter() - started
    return {
        **results,
        "registry_version": registry.version,
        "mode": mode,
        "staggered": True,
        "exchange_count": len(entries),
        "elapsed_sec": round(elapsed, 3),
    }
