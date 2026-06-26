"""DEX swap plugin contracts (S23)."""

from __future__ import annotations

from typing import Any, Protocol


class SwapPlugin(Protocol):
    protocol: str
    venue_id: str

    def preview_swap(
        self,
        sell_token: str,
        buy_token: str,
        sell_amount: float,
    ) -> dict[str, Any]: ...

    def simulate_swap(
        self,
        sell_token: str,
        buy_token: str,
        sell_amount: float,
    ) -> dict[str, Any]: ...

    def execute_live_swap(
        self,
        sell_token: str,
        buy_token: str,
        sell_amount: float,
        *,
        slippage_bps: int,
        nonce: int,
        signed_tx_hash: str,
    ) -> dict[str, Any]: ...
