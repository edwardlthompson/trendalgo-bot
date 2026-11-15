"""Persist DEX pool-watch rows for the device (DEX-P2a)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from trendalgo.venues.dex_watch_types import PoolWatchSnapshot

DEX_WATCH_ROWS_FILE = "dex_watch_rows.json"


def dex_watch_rows_path(root: Path) -> Path:
    return Path(root) / DEX_WATCH_ROWS_FILE


def save_dex_watch_rows(root: Path, rows: list[dict[str, Any]]) -> None:
    path = dex_watch_rows_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"rows": rows}, indent=2) + "\n", encoding="utf-8")


def load_dex_watch_rows(root: Path) -> list[dict[str, Any]]:
    path = dex_watch_rows_path(root)
    if not path.is_file():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    rows = raw.get("rows") if isinstance(raw, dict) else raw
    return list(rows) if isinstance(rows, list) else []


def pool_rows_to_device_coins(snapshot: PoolWatchSnapshot) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in snapshot.rows:
        out.append(
            {
                "pair": row.pair,
                "exchange_id": row.venue_id,
                "listed_on": [row.venue_id],
                "pool_address": row.pool_address,
                "liquidity_usd": row.liquidity_usd,
                "price_change_24h_pct": row.price_change_24h_pct,
                "volume_proxy_usd": row.volume_proxy_usd,
                "degraded": row.degraded,
                "source": row.source,
                "chart_closes": [],
                "scan_mode": "dex_watch",
            }
        )
    return out
