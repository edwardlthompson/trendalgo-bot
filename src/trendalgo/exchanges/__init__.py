"""Exchange registry and portfolio adapter protocol (S13)."""

from trendalgo.exchanges.registry import (
    ExchangeEntry,
    get_entry,
    list_exchanges,
    list_portfolio_exchanges,
    list_trading_exchanges,
    list_worldwide_trading_exchanges,
    load_registry,
)

__all__ = [
    "ExchangeEntry",
    "get_entry",
    "list_exchanges",
    "list_portfolio_exchanges",
    "list_trading_exchanges",
    "list_worldwide_trading_exchanges",
    "load_registry",
]
