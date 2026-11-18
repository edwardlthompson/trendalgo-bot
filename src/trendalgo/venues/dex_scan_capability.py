"""Which DEX venues expose thin public pool watch without keys (DEX-P2a)."""

from __future__ import annotations

from dataclasses import dataclass

_POOL_WATCH: frozenset[str] = frozenset({"ethereum", "base"})


@dataclass(frozen=True)
class DexScanCapability:
    venue_id: str
    pool_watch_without_keys: bool
    opportunity_desk: bool
    note: str


def dex_scan_capability(venue_id: str) -> DexScanCapability:
    vid = str(venue_id or "").strip().lower()
    watch = vid in _POOL_WATCH
    if watch:
        note = "Thin Uniswap V3 pool watch (RPC or dry-run); not Opportunity/All-TA."
    else:
        note = "No public pool watch in this phase."
    return DexScanCapability(
        venue_id=vid,
        pool_watch_without_keys=watch,
        opportunity_desk=False,
        note=note,
    )


def dex_pool_watch_venues() -> tuple[str, ...]:
    return ("ethereum", "base")
