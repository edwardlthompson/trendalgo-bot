"""Uniswap V3 swap simulation — EVM chains, dry-run only (S23)."""

from __future__ import annotations

import hashlib
import uuid
from typing import Any

from trendalgo.venues.base import VenueEntry


class UniswapV3SwapPlugin:
    protocol = "uniswap_v3"
    venue_id: str

    def __init__(self, entry: VenueEntry) -> None:
        self.entry = entry
        self.venue_id = entry.id

    def _quote(
        self,
        sell_token: str,
        buy_token: str,
        sell_amount: float,
        *,
        simulated: bool,
    ) -> dict[str, Any]:
        seed = hashlib.sha256(
            f"uni-swap:{self.venue_id}:{sell_token}:{buy_token}:{sell_amount}".encode()
        ).hexdigest()
        slippage_bps = int(seed[:4], 16) % 30
        base_price = 3000.0 if sell_token.upper() in {"ETH", "WETH"} else 1.0
        price = base_price * (1 - slippage_bps / 10000)
        buy_amount = round(sell_amount * price, 8)
        payload: dict[str, Any] = {
            "chain": self.venue_id,
            "protocol": self.protocol,
            "sell_token": sell_token.upper(),
            "buy_token": buy_token.upper(),
            "sell_amount": sell_amount,
            "buy_amount": buy_amount,
            "price": round(price, 8),
            "slippage_bps": slippage_bps,
            "gas_estimate_usd": round(int(seed[4:8], 16) / 50, 2),
            "tx_broadcast": False,
        }
        if simulated:
            payload["mode"] = "simulated"
            payload["simulation_id"] = f"dex-sim-{uuid.uuid4().hex[:12]}"
        else:
            payload["mode"] = "preview"
            payload["read_only"] = True
        return payload

    def preview_swap(self, sell_token: str, buy_token: str, sell_amount: float) -> dict[str, Any]:
        return self._quote(sell_token, buy_token, sell_amount, simulated=False)

    def simulate_swap(self, sell_token: str, buy_token: str, sell_amount: float) -> dict[str, Any]:
        return self._quote(sell_token, buy_token, sell_amount, simulated=True)

    def execute_live_swap(
        self,
        sell_token: str,
        buy_token: str,
        sell_amount: float,
        *,
        slippage_bps: int,
        nonce: int,
        signed_tx_hash: str,
    ) -> dict[str, Any]:
        quote = self._quote(sell_token, buy_token, sell_amount, simulated=True)
        quote["mode"] = "live"
        quote["slippage_bps"] = slippage_bps
        quote["nonce"] = nonce
        quote["tx_hash"] = signed_tx_hash
        quote["tx_broadcast"] = True
        quote.pop("simulation_id", None)
        return quote
