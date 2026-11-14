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
    watchlist: set[str] | None = None,  # noqa: ARG001 — kept for call-site compat
    previous_coins: dict[str, dict[str, Any]] | None = None,
    board_coins: list[dict[str, Any]] | None = None,
    floors: dict[str, float] | None = None,
) -> list[AlertEvent]:
    """New filtered enters + every coin that left the filtered Qualified set.

    Kind remains ``watchlist_leave`` for NotifyPrefs / history compatibility.
    Leave reasons prefer current full-board metrics when the coin is still
    scan-qualified but filtered out.
    """
    del watchlist  # leave is filtered-set based, not watchlist-gated
    by_key = coins_by_key(current_coins)
    current = set(by_key)
    prev_coins = previous_coins or {}
    board_by_key = coins_by_key(board_coins) if board_coins else {}
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
    for key in sorted(previous - current):
        snap = board_by_key.get(key) or prev_coins.get(key)
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
    """Field-level leave reason from last snapshot vs Qualified-column floors."""
    if snap is None:
        return f"{symbol} left the qualified list (not in qualified set)"
    floors = floors or {}
    parts: list[str] = []
    vol = _num(snap.get("volume_24h") or snap.get("volume_usd"))
    min_vol = _floor(floors, "vol24_min", "min_volume_usd")
    if min_vol is not None and vol is not None and vol < min_vol:
        parts.append(f"Volume ${vol:,.0f} below min ${min_vol:,.0f}")
    uni = _num(snap.get("uniformity_score") or snap.get("uniformity"))
    min_uni = _floor(floors, "uniformity_min", "min_uniformity")
    if min_uni is not None and uni is not None and uni < min_uni:
        parts.append(f"Uniformity {uni:.2f} < {min_uni:.2f}")
    gains = snap.get("gains") if isinstance(snap.get("gains"), dict) else {}
    gain7 = _num(snap.get("gain_7d") or gains.get("7d"))
    min_g7 = _floor(floors, "min_gain_7d")
    if min_g7 is not None and gain7 is not None:
        g7_pct, floor7 = _pct_pair(gain7, min_g7)
        if g7_pct < floor7:
            parts.append(f"7D gain {g7_pct:.1f}% below min {floor7:.1f}%")
    gain30 = _num(snap.get("gain_30d") or gains.get("30d") or snap.get("gain_pct"))
    min_g30 = _floor(floors, "min_gain_30d", "min_gain_pct")
    if min_g30 is not None and gain30 is not None:
        g30_pct, floor30 = _pct_pair(gain30, min_g30)
        if g30_pct < floor30:
            parts.append(f"30D gain {g30_pct:.1f}% below min {floor30:.1f}%")
    best = _num(snap.get("bot_best_net_pct"))
    min_bt = _floor(floors, "min_best_bt")
    if min_bt is not None and best is not None and best < min_bt:
        parts.append(f"Best BT {best:.1f}% below min {min_bt:.1f}%")
    health = _num(snap.get("health_score") or snap.get("health"))
    min_health = _floor(floors, "health_min", "min_health")
    if min_health is not None and health is not None and health < min_health:
        parts.append(f"Health {health:.2f} < {min_health:.2f}")
    for key, label in (
        ("chart_dist_max_7d", "7d chart dist"),
        ("chart_dist_max_30d", "30d chart dist"),
    ):
        cap = _floor(floors, key)
        field = "chart_dist_7d_pct" if "7d" in key else "chart_dist_30d_pct"
        dist = _num(snap.get(field))
        if cap is not None and dist is not None and dist > cap:
            parts.append(f"{label} {dist:.1f}% above max {cap:.1f}%")
    if parts:
        return f"{symbol} left qualified: " + "; ".join(parts)
    return f"{symbol} left the qualified list (dropped from qualified set)"


def _floor(floors: dict[str, float], *keys: str) -> float | None:
    for key in keys:
        if key in floors and floors[key] is not None:
            try:
                return float(floors[key])
            except (TypeError, ValueError):
                continue
    return None


def _pct_pair(value: float, floor: float) -> tuple[float, float]:
    """Normalize gain/floor that may be fraction (0.2) or percent (20)."""
    floor_pct = floor * 100.0 if floor <= 1.0 else floor
    value_pct = value * 100.0 if abs(value) <= 1.5 else value
    return value_pct, floor_pct


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
