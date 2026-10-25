"""Map Secret Sauce RegimeSnapshot axes → user-facing Market Context labels."""

from __future__ import annotations

from typing import Any


def user_regime_label(
    *,
    structural: str,
    direction: str,
    volatility: str,
    squeeze: bool,
) -> str:
    """One primary label for the Signal zone chip."""
    if squeeze or (volatility == "low" and structural in {"ranging", "transitional"}):
        return "Compressing"
    if volatility == "high" and structural in {"choppy", "ranging", "transitional"}:
        return "Volatile"
    if structural == "trending":
        if direction == "up":
            return "Trending Up"
        if direction == "down":
            return "Trending Down"
        return "Trending Up" if direction != "down" else "Trending Down"
    if structural == "ranging":
        return "Ranging"
    if structural == "choppy":
        return "Volatile"
    if direction == "up":
        return "Trending Up"
    if direction == "down":
        return "Trending Down"
    return "Ranging"


def label_from_regime_dict(regime: dict[str, Any] | None) -> str:
    if not isinstance(regime, dict):
        return "Ranging"
    return user_regime_label(
        structural=str(regime.get("structural") or "ranging"),
        direction=str(regime.get("direction") or "flat"),
        volatility=str(regime.get("volatility") or "normal"),
        squeeze=bool(regime.get("squeeze")),
    )
