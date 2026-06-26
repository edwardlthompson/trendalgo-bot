"""Registry-driven CCXT trading adapter — dry-run default (S16)."""

from __future__ import annotations

import os
import uuid
from typing import Any

import ccxt

from trendalgo.exchanges.registry import ExchangeEntry, get_entry


class GenericCcxtTradingAdapter:
    """Spot order adapter for any registry exchange with trading_enabled."""

    def __init__(self, entry: ExchangeEntry) -> None:
        self.entry = entry
        self.exchange_id = entry.id

    def _client(self) -> Any:
        exchange_class = getattr(ccxt, self.entry.ccxt_id, None)
        if exchange_class is None:
            raise ValueError(f"ccxt has no exchange class: {self.entry.ccxt_id}")
        options: dict[str, Any] = {"enableRateLimit": True}
        if self.entry.id == "kraken":
            options["options"] = {"adjustForTimeDifference": True}
        return exchange_class(
            {
                "apiKey": os.environ.get(self.entry.env_key, ""),
                "secret": os.environ.get(self.entry.env_secret, ""),
                **options,
            }
        )

    def simulate_order(
        self,
        pair: str,
        side: str,
        amount_usd: float,
        price: float,
    ) -> dict[str, Any]:
        amount = amount_usd / price if price > 0 else 0.0
        return {
            "exchange": self.exchange_id,
            "pair": pair,
            "side": side,
            "amount_usd": round(amount_usd, 2),
            "amount": round(amount, 8),
            "price": price,
            "mode": "dry_run",
            "status": "simulated",
            "order_id": f"dry-{self.exchange_id}-{uuid.uuid4().hex[:12]}",
        }

    def submit_order(
        self,
        pair: str,
        side: str,
        amount_usd: float,
        price: float,
    ) -> dict[str, Any]:
        if not self.entry.has_api_keys():
            raise ValueError(f"{self.exchange_id}: API keys required for live orders")
        exchange = self._client()
        amount = amount_usd / price if price > 0 else 0.0
        order = exchange.create_order(pair, "market", side, amount)
        return {
            "exchange": self.exchange_id,
            "pair": pair,
            "side": side,
            "amount_usd": round(amount_usd, 2),
            "mode": "live",
            "status": str(order.get("status", "submitted")),
            "order_id": str(order.get("id", "")),
        }
