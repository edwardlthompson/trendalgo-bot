"""Run curated Uniswap/Base pool watch (DEX-P2a)."""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path

from trendalgo.venues.dex_scan_capability import dex_pool_watch_venues
from trendalgo.venues.dex_watch_types import PoolWatchRow, PoolWatchSnapshot, WatchPoolRef
from trendalgo.venues.registry import get_venue
from trendalgo.venues.uniswap_v3_pool_watch import dry_run_metrics

PoolWatchRunner = Callable[[WatchPoolRef], PoolWatchRow]

_DEFAULT_POOLS = Path(__file__).resolve().parents[3] / "config" / "dex_watch_pools.json"


def load_watch_pools(
    venue_id: str, *, registry_path: Path | None = None
) -> tuple[WatchPoolRef, ...]:
    path = registry_path or _DEFAULT_POOLS
    raw = json.loads(path.read_text(encoding="utf-8"))
    rows: list[WatchPoolRef] = []
    for item in raw.get("pools") or []:
        if str(item.get("venue_id") or "").lower() != venue_id.lower():
            continue
        rows.append(
            WatchPoolRef(
                venue_id=str(item["venue_id"]).lower(),
                pool_address=str(item["pool_address"]).lower(),
                pair=str(item["pair"]),
                fee_tier=int(item.get("fee_tier") or 0),
            )
        )
    return tuple(rows)


def fetch_pool_row(
    pool: WatchPoolRef,
    *,
    dry_run: bool = True,
) -> PoolWatchRow:
    """Build one watch row. v1 always uses deterministic dry metrics (no RPC)."""
    _ = dry_run
    entry = get_venue(pool.venue_id)
    liq, chg, vol = dry_run_metrics(pool.pool_address, pool.pair)
    return PoolWatchRow(
        venue_id=entry.id,
        pool_address=pool.pool_address,
        pair=pool.pair,
        liquidity_usd=liq,
        price_change_24h_pct=chg,
        volume_proxy_usd=vol,
        degraded=True,  # honest: not live slot0/volume yet
        source=f"{entry.id}_dry_run",
    )


def run_pool_watch_scan(
    venue_ids: Sequence[str] | None = None,
    *,
    runner: PoolWatchRunner | None = None,
) -> PoolWatchSnapshot:
    ids = tuple(venue_ids) if venue_ids is not None else dex_pool_watch_venues()
    allowed = set(dex_pool_watch_venues())
    fetch = runner or (lambda p: fetch_pool_row(p, dry_run=True))
    rows: list[PoolWatchRow] = []
    for vid in ids:
        if vid not in allowed:
            continue
        for pool in load_watch_pools(vid):
            rows.append(fetch(pool))
    rows.sort(key=lambda r: -(r.volume_proxy_usd or 0.0))
    degraded = not rows or any(r.degraded for r in rows)
    return PoolWatchSnapshot(
        generated_at=datetime.now(UTC),
        rows=tuple(rows),
        degraded=degraded,
    )
