"""Binance.US read-only portfolio adapter (S13) — generic-backed (S14)."""

from __future__ import annotations

from trendalgo.exchanges.adapters.generic import GenericCcxtPortfolioAdapter
from trendalgo.exchanges.registry import get_entry


class BinanceUSAdapter(GenericCcxtPortfolioAdapter):
    exchange_id = "binanceus"

    def __init__(self) -> None:
        super().__init__(get_entry("binanceus"))
