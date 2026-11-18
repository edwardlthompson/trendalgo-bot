"""DEX candle result types (DEX-P2b) — labeled aggregator / CEX proxy / synthetic."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from trendalgo.market.types import OhlcvPoint

DexCandleKind = Literal["aggregator", "cex_proxy", "synthetic"]


@dataclass(frozen=True)
class DexPairRef:
    venue_id: str
    pair: str
    pool_address: str
    fee_tier: int


@dataclass(frozen=True)
class DexCandleSourceMeta:
    venue_id: str
    pair: str
    kind: DexCandleKind
    provider_id: str
    cache_source: str
    pool_address: str | None
    degraded: bool
    disclaimer: str


@dataclass(frozen=True)
class DexCandleResult:
    points: tuple[OhlcvPoint, ...]
    meta: DexCandleSourceMeta
