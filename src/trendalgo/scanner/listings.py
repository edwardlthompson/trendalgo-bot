"""Kraken spot listing verification (O2)."""

from __future__ import annotations

DEFAULT_KRAKEN_SPOT = ("BTC/USD", "ETH/USD", "SOL/USD", "ADA/USD", "DOT/USD")


def verify_kraken_listings(pairs: tuple[str, ...] | None = None) -> list[str]:
    """Return normalized pairs available on Kraken spot MVP universe."""
    source = pairs or DEFAULT_KRAKEN_SPOT
    return [p.replace("USDT", "USD") for p in source if "/" in p]
