"""Device job: thin Uniswap/Base pool watch (DEX-P2a)."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from trendalgo.device.dex_watch_model import pool_rows_to_device_coins, save_dex_watch_rows
from trendalgo.venues.dex_watch_types import PoolWatchSnapshot
from trendalgo.venues.pool_watch_scan import run_pool_watch_scan


def dex_watch_scan_job(
    root: Path,
    *,
    scanner: Callable[..., PoolWatchSnapshot] | None = None,
) -> dict[str, Any]:
    snap = scanner() if scanner is not None else run_pool_watch_scan()
    rows = pool_rows_to_device_coins(snap)
    save_dex_watch_rows(root, rows)
    venues = sorted({str(r.get("exchange_id") or "") for r in rows if r.get("exchange_id")})
    return {
        "rows": len(rows),
        "venues": venues,
        "degraded": bool(snap.degraded),
        "scan_mode": "dex_watch",
        "data_source": "uniswap_v3_pool_watch",
    }
