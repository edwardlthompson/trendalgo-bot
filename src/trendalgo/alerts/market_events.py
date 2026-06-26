"""Market event alerts — price %, volume spike (T21)."""

from __future__ import annotations

from typing import Any


def evaluate_market_event(
    pair: str,
    price_change_pct: float,
    volume_ratio: float,
    *,
    price_threshold: float = 0.03,
    volume_threshold: float = 2.0,
) -> dict[str, Any] | None:
    if abs(price_change_pct) >= price_threshold:
        return {
            "type": "price_move",
            "pair": pair,
            "message": f"{pair} price change {price_change_pct * 100:.1f}%",
            "severity": "high" if abs(price_change_pct) >= 0.05 else "medium",
        }
    if volume_ratio >= volume_threshold:
        return {
            "type": "volume_spike",
            "pair": pair,
            "message": f"{pair} volume {volume_ratio:.1f}x average",
            "severity": "medium",
        }
    return None
