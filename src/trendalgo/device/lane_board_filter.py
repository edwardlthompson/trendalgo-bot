"""Keep each scanner desk's board rows on that lane (no crypto on Forex, etc.)."""

from __future__ import annotations

from typing import Any

from trendalgo.brokers.forex_universe import is_forex_pair
from trendalgo.device.scan_identity import coin_exchange_id

_CRYPTO_VENUES = frozenset({"kraken", "coinbase", "binance"})
_LANE_STAMPS = frozenset({"tradfi", "forex"})


def filter_lane_coins(rows: list[dict[str, Any]], lane: str) -> list[dict[str, Any]]:
    """Drop cross-lane bleed before the board paints."""
    key = (lane or "crypto").strip().lower()
    if key == "forex":
        return [
            r
            for r in rows
            if is_forex_pair(str(r.get("pair") or "")) or coin_exchange_id(r) == "forex"
        ]
    if key == "tradfi":
        return [
            r
            for r in rows
            if coin_exchange_id(r) == "tradfi"
            or (
                coin_exchange_id(r) not in _CRYPTO_VENUES | {"forex"}
                and not is_forex_pair(str(r.get("pair") or ""))
            )
        ]
    return [
        r
        for r in rows
        if coin_exchange_id(r) not in _LANE_STAMPS and not is_forex_pair(str(r.get("pair") or ""))
    ]
