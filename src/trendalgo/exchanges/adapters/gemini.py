"""Gemini portfolio adapter — dedicated GUSD/USD aliases (CEX-P1b)."""

from __future__ import annotations

from trendalgo.exchanges.adapters.generic import GenericCcxtPortfolioAdapter
from trendalgo.exchanges.registry import get_entry


class GeminiAdapter(GenericCcxtPortfolioAdapter):
    """Gemini spot balances.

    Pins GUSD as a USD cash alias so stable inventory is not priced as a risk asset.
    """

    exchange_id = "gemini"

    def __init__(self) -> None:
        super().__init__(get_entry("gemini"))

    def _usd_aliases(self) -> frozenset[str]:
        return frozenset({*self.entry.usd_aliases, "GUSD", "USD"})
