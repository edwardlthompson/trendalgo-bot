"""Normalize trading pair / symbol strings for market data fetch."""

from __future__ import annotations


def base_symbol(pair_or_symbol: str) -> str:
    raw = pair_or_symbol.strip().upper()
    if "/" in raw:
        return raw.split("/", 1)[0]
    if "-" in raw:
        return raw.split("-", 1)[0]
    return raw


def quote_symbol(pair_or_symbol: str, default: str = "USD") -> str:
    raw = pair_or_symbol.strip().upper()
    if "/" in raw:
        return raw.split("/", 1)[1]
    if "-" in raw:
        return raw.split("-", 1)[1]
    return default
