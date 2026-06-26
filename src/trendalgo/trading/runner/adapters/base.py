"""Native trading adapter protocol (S16)."""

from __future__ import annotations

from typing import Any, Protocol


class TradingAdapter(Protocol):
    exchange_id: str

    def simulate_order(
        self,
        pair: str,
        side: str,
        amount_usd: float,
        price: float,
    ) -> dict[str, Any]: ...

    def submit_order(
        self,
        pair: str,
        side: str,
        amount_usd: float,
        price: float,
    ) -> dict[str, Any]: ...
