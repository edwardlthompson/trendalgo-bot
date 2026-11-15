"""Coinbase Advanced portfolio adapter — dedicated USD/USDC alias + fee path (CEX-P1b)."""

from __future__ import annotations

from trendalgo.exchanges.adapters.generic import GenericCcxtPortfolioAdapter
from trendalgo.exchanges.registry import get_entry


class CoinbaseAdvancedAdapter(GenericCcxtPortfolioAdapter):
    """Coinbase Advanced Trade (ccxt id ``coinbase``).

    Generic CCXT works for balances; this adapter pins retail USD aliases
    (USDC settles as cash) and keeps a typed entry point for auth/fee quirks.
    """

    exchange_id = "coinbaseadvanced"

    def __init__(self) -> None:
        super().__init__(get_entry("coinbaseadvanced"))

    def _usd_aliases(self) -> frozenset[str]:
        return frozenset({*self.entry.usd_aliases, "USDC", "USD"})
