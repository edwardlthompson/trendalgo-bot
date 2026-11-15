"""Curated DEX major pairs from dex_watch_pools.json (DEX-P2b)."""

from __future__ import annotations

import json
from pathlib import Path

from trendalgo.market.dex_candle_types import DexPairRef

DEX_CANDLE_VENUES: tuple[str, ...] = ("ethereum", "base")
_DEFAULT_POOLS = Path(__file__).resolve().parents[3] / "config" / "dex_watch_pools.json"


def list_dex_candle_pairs(
    venue_id: str, *, pools_path: Path | None = None
) -> tuple[DexPairRef, ...]:
    vid = venue_id.strip().lower()
    if vid not in DEX_CANDLE_VENUES:
        return ()
    path = pools_path or _DEFAULT_POOLS
    raw = json.loads(path.read_text(encoding="utf-8"))
    out: list[DexPairRef] = []
    seen: set[str] = set()
    for item in raw.get("pools") or []:
        if str(item.get("venue_id") or "").lower() != vid:
            continue
        pair = str(item.get("pair") or "")
        addr = str(item.get("pool_address") or "").lower()
        key = f"{pair}|{addr}"
        if key in seen:
            continue
        seen.add(key)
        out.append(
            DexPairRef(
                venue_id=vid,
                pair=pair,
                pool_address=addr,
                fee_tier=int(item.get("fee_tier") or 0),
            )
        )
    return tuple(out)
