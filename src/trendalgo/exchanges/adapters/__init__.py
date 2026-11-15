"""Exchange portfolio adapters."""

from trendalgo.exchanges.adapters.binanceus import BinanceUSAdapter
from trendalgo.exchanges.adapters.coinbaseadvanced import CoinbaseAdvancedAdapter
from trendalgo.exchanges.adapters.factory import portfolio_adapter_for
from trendalgo.exchanges.adapters.gemini import GeminiAdapter
from trendalgo.exchanges.adapters.generic import GenericCcxtPortfolioAdapter
from trendalgo.exchanges.adapters.kraken import KrakenAdapter

__all__ = [
    "BinanceUSAdapter",
    "CoinbaseAdvancedAdapter",
    "GeminiAdapter",
    "GenericCcxtPortfolioAdapter",
    "KrakenAdapter",
    "portfolio_adapter_for",
]
