"""Multi-chain DEX ops load tests (CM-6, S24)."""

from __future__ import annotations

import os
import tempfile
import uuid
from pathlib import Path

from trendalgo.portfolio.db import PortfolioStore
from trendalgo.venues.orchestrator import sync_all_wallet_venues
from trendalgo.venues.registry import list_wallet_venues, load_venue_registry

MIN_VENUES = 4
MAX_ELAPSED_SEC = 30.0
EVM_ADDR = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0"


def run_dex_sync_load_test(
    *, min_venues: int = MIN_VENUES, max_sec: float = MAX_ELAPSED_SEC
) -> dict[str, object]:
    os.environ.setdefault("TRENDALGO_VENUE_SYNC_STAGGER_SEC", "0")
    tmp = Path(tempfile.gettempdir()) / f"trendalgo-dex-load-{uuid.uuid4().hex}"
    tmp.mkdir(parents=True, exist_ok=True)
    db_path = tmp / "portfolio.db"
    store = PortfolioStore(db_path)
    try:
        result = sync_all_wallet_venues(store, EVM_ADDR, dry_run=True, include_lp=True)
    finally:
        del store
        try:
            db_path.unlink(missing_ok=True)
            tmp.rmdir()
        except OSError:
            pass
    elapsed = float(result.get("elapsed_sec", 999))
    count = int(result.get("venue_count", 0))
    synced = int(result.get("synced_count", 0))
    ok = count >= min_venues and synced >= 3 and elapsed < max_sec
    return {
        "ok": ok,
        "venue_count": count,
        "synced_count": synced,
        "elapsed_sec": elapsed,
        "max_sec": max_sec,
        "min_venues": min_venues,
        "registry_version": result.get("registry_version"),
    }


def run_dex_trading_status_check(*, min_live_phase: int = 1) -> dict[str, object]:
    registry = load_venue_registry()
    swap_venues = [v.id for v in list_wallet_venues() if v.swap_plugins]
    live = [v.id for v in list_wallet_venues() if v.trading_enabled and v.swap_plugins]
    phase = registry.dex_live_phase
    ok = registry.version >= 4 and len(swap_venues) >= 4 and phase >= min_live_phase
    return {
        "ok": ok,
        "registry_version": registry.version,
        "dex_live_phase": phase,
        "swap_venue_count": len(swap_venues),
        "live_trading_venues": live,
        "swap_venues": swap_venues,
    }


def run_dex_ops_validation(
    *, min_venues: int = MIN_VENUES, max_sec: float = MAX_ELAPSED_SEC
) -> dict[str, object]:
    """S24 CM-6: multi-chain wallet sync + DEX trading status gates."""
    sync = run_dex_sync_load_test(min_venues=min_venues, max_sec=max_sec)
    trading = run_dex_trading_status_check()
    ok = bool(sync["ok"] and trading["ok"])
    return {"ok": ok, "wallet_sync": sync, "trading_status": trading}
