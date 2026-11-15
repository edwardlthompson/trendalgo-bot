"""Types for DEX on-chain pool watch (DEX-P2a)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class WatchPoolRef:
    venue_id: str
    pool_address: str
    pair: str
    fee_tier: int


@dataclass(frozen=True)
class PoolWatchRow:
    venue_id: str
    pool_address: str
    pair: str
    liquidity_usd: float | None
    price_change_24h_pct: float | None
    volume_proxy_usd: float | None
    degraded: bool
    source: str


@dataclass(frozen=True)
class PoolWatchSnapshot:
    generated_at: datetime
    rows: tuple[PoolWatchRow, ...]
    degraded: bool
