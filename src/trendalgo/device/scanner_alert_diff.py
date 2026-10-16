"""Compare qualified sets across scans for enter/leave alerts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AlertEvent:
    kind: str  # qualified_enter | watchlist_leave
    symbol: str
    pair: str
    reason: str
    coin: dict[str, Any] | None = None


def coin_keys(coins: list[dict[str, Any]]) -> set[str]:
    """Normalized symbol keys for qualified coins."""
    out: set[str] = set()
    for coin in coins:
        key = _key(coin)
        if key:
            out.add(key)
    return out


def watchlist_keys(pairs: list[str]) -> set[str]:
    out: set[str] = set()
    for raw in pairs:
        text = str(raw or "").strip().upper()
        if not text:
            continue
        out.add(text.split("/", 1)[0] if "/" in text else text)
    return out


def diff_alerts(
    *,
    previous: set[str],
    current_coins: list[dict[str, Any]],
    watchlist: set[str],
) -> list[AlertEvent]:
    """New qualified enters + watchlisted coins that left qualified."""
    by_key = {_key(c): c for c in current_coins if _key(c)}
    current = set(by_key)
    events: list[AlertEvent] = []
    for key in sorted(current - previous):
        coin = by_key[key]
        events.append(
            AlertEvent(
                kind="qualified_enter",
                symbol=key,
                pair=str(coin.get("pair") or key),
                reason="Entered the qualified list",
                coin=coin,
            )
        )
    for key in sorted((previous & watchlist) - current):
        events.append(
            AlertEvent(
                kind="watchlist_leave",
                symbol=key,
                pair=f"{key}/USD",
                reason=_leave_reason(key, current_coins),
                coin=None,
            )
        )
    return events


def _leave_reason(symbol: str, _current: list[dict[str, Any]]) -> str:
    return f"{symbol} left the qualified list (no longer meets scan floors)"


def _key(coin: dict[str, Any]) -> str:
    symbol = str(coin.get("symbol") or "").strip().upper()
    if symbol:
        return symbol
    pair = str(coin.get("pair") or "").strip().upper()
    return pair.split("/", 1)[0] if "/" in pair else pair
