"""Resolve dedicated portfolio adapters (falls back to generic CCXT)."""

from __future__ import annotations

from collections.abc import Callable

from trendalgo.exchanges.adapters.binanceus import BinanceUSAdapter
from trendalgo.exchanges.adapters.coinbaseadvanced import CoinbaseAdvancedAdapter
from trendalgo.exchanges.adapters.gemini import GeminiAdapter
from trendalgo.exchanges.adapters.generic import GenericCcxtPortfolioAdapter
from trendalgo.exchanges.adapters.kraken import KrakenAdapter
from trendalgo.exchanges.registry import get_entry

_DEDICATED: dict[str, Callable[[], GenericCcxtPortfolioAdapter]] = {
    "kraken": KrakenAdapter,
    "binanceus": BinanceUSAdapter,
    "coinbaseadvanced": CoinbaseAdvancedAdapter,
    "gemini": GeminiAdapter,
}


def portfolio_adapter_for(exchange_id: str) -> GenericCcxtPortfolioAdapter:
    eid = str(exchange_id or "").strip().lower()
    factory = _DEDICATED.get(eid)
    if factory is not None:
        return factory()
    return GenericCcxtPortfolioAdapter(get_entry(eid))
