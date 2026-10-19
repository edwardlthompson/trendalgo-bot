"""Compare qualified sets across scans for enter/leave alerts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AlertEvent:
    kind: str  # qualified_enter | watchlist_leave | scan_log | backtest_log | trade_alert
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


def coins_by_key(coins: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {k: c for c in coins if (k := _key(c))}


def diff_alerts(
    *,
    previous: set[str],
    current_coins: list[dict[str, Any]],
    watchlist: set[str],
    previous_coins: dict[str, dict[str, Any]] | None = None,
    floors: dict[str, float] | None = None,
) -> list[AlertEvent]:
    """New qualified enters + watchlisted coins that left qualified."""
    by_key = coins_by_key(current_coins)
    current = set(by_key)
    prev_coins = previous_coins or {}
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
        snap = prev_coins.get(key)
        events.append(
            AlertEvent(
                kind="watchlist_leave",
                symbol=key,
                pair=str((snap or {}).get("pair") or f"{key}/USD"),
                reason=leave_reason(key, snap, floors=floors),
                coin=snap,
            )
        )
    return events


def leave_reason(
    symbol: str,
    snap: dict[str, Any] | None,
    *,
    floors: dict[str, float] | None = None,
) -> str:
    """Field-level leave reason from last snapshot vs scan floors."""
    if snap is None:
        return f"{symbol} left the qualified list (not in qualified set)"
    floors = floors or {}
    parts: list[str] = []
    vol = _num(snap.get("volume_24h") or snap.get("volume_usd"))
    min_vol = floors.get("min_volume_usd")
    if min_vol is not None and vol is not None and vol < min_vol:
        parts.append(f"Volume ${vol:,.0f} below min ${min_vol:,.0f}")
    uni = _num(snap.get("uniformity_score") or snap.get("uniformity"))
    min_uni = floors.get("min_uniformity")
    if min_uni is not None and uni is not None and uni < min_uni:
        parts.append(f"Uniformity {uni:.2f} < {min_uni:.2f}")
    gain30 = _num(snap.get("gain_30d") or snap.get("gain_pct"))
    min_gain = floors.get("min_gain_30d") or floors.get("min_gain_pct")
    if min_gain is not None and gain30 is not None:
        # floors may be fraction (0.2) or percent (20)
        floor_pct = min_gain * 100.0 if min_gain <= 1.0 else min_gain
        gain_pct = gain30 * 100.0 if abs(gain30) <= 1.5 else gain30
        if gain_pct < floor_pct:
            parts.append(f"30D gain {gain_pct:.1f}% below min {floor_pct:.1f}%")
    health = _num(snap.get("health"))
    min_health = floors.get("min_health")
    if min_health is not None and health is not None and health < min_health:
        parts.append(f"Health {health:.2f} < {min_health:.2f}")
    if parts:
        return f"{symbol} left qualified: " + "; ".join(parts)
    return f"{symbol} left the qualified list (dropped from qualified set)"


def _num(raw: Any) -> float | None:
    if raw in (None, "", "-"):
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _key(coin: dict[str, Any]) -> str:
    symbol = str(coin.get("symbol") or "").strip().upper()
    if symbol:
        return symbol
    pair = str(coin.get("pair") or "").strip().upper()
    return pair.split("/", 1)[0] if pair else ""
