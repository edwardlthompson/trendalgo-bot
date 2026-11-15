"""DEX-P2a: Uniswap/Base thin pool watch."""

from __future__ import annotations

from trendalgo.venues.dex_scan_capability import dex_pool_watch_venues, dex_scan_capability
from trendalgo.venues.pool_watch_scan import load_watch_pools, run_pool_watch_scan


def test_dex_pool_watch_venues_ethereum_base_only() -> None:
    assert dex_pool_watch_venues() == ("ethereum", "base")
    assert dex_scan_capability("base").pool_watch_without_keys
    assert not dex_scan_capability("base").opportunity_desk
    assert not dex_scan_capability("arbitrum").pool_watch_without_keys


def test_load_watch_pools_curated() -> None:
    eth = load_watch_pools("ethereum")
    base = load_watch_pools("base")
    assert len(eth) >= 1
    assert len(base) >= 1
    assert all(p.venue_id == "ethereum" for p in eth)


def test_run_pool_watch_scan_degraded_dry_run() -> None:
    snap = run_pool_watch_scan()
    assert snap.rows
    assert snap.degraded
    venues = {r.venue_id for r in snap.rows}
    assert venues == {"ethereum", "base"}
    assert all(r.source.endswith("_dry_run") for r in snap.rows)
