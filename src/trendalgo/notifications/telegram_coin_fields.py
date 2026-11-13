"""Resolve LTS-shaped coin fields for Telegram captions and charts."""

from __future__ import annotations

from typing import Any


def coin_symbol(coin: dict[str, Any]) -> str:
    return (
        str(coin.get("symbol") or coin.get("pair") or "?").split("/", 1)[0].strip().upper() or "?"
    )


def coin_name(coin: dict[str, Any]) -> str:
    return str(coin.get("name") or coin.get("full_name") or coin_symbol(coin))


def coin_pair(coin: dict[str, Any]) -> str:
    return str(coin.get("pair") or f"{coin_symbol(coin)}/USD")


def gain_pct(coin: dict[str, Any], window: str) -> float | None:
    direct = coin.get(f"gain_{window}")
    if isinstance(direct, (int, float)):
        return float(direct)
    gains = coin.get("gains")
    if isinstance(gains, dict) and gains.get(window) is not None:
        try:
            return float(gains[window])
        except (TypeError, ValueError):
            return None
    return None


def health_score(coin: dict[str, Any]) -> float | None:
    raw = coin.get("health_score", coin.get("health"))
    try:
        return float(raw) if raw is not None and raw != "" else None
    except (TypeError, ValueError):
        return None


def uniformity_score(coin: dict[str, Any]) -> float | None:
    raw = coin.get("uniformity_score", coin.get("uniformity"))
    try:
        return float(raw) if raw is not None and raw != "" else None
    except (TypeError, ValueError):
        return None


def volume_24h(coin: dict[str, Any]) -> float | None:
    raw = coin.get("volume_24h", coin.get("vol24"))
    try:
        return float(raw) if raw is not None and raw != "" else None
    except (TypeError, ValueError):
        return None


def listed_exchanges(coin: dict[str, Any]) -> list[str]:
    raw = coin.get("listed_on") or []
    if isinstance(raw, list):
        return [str(x).strip().lower() for x in raw if str(x).strip()]
    return []


def exchange_volumes(coin: dict[str, Any]) -> dict[str, Any]:
    raw = coin.get("exchange_volumes")
    return dict(raw) if isinstance(raw, dict) else {}
