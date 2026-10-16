"""Registry-driven CCXT trading adapter — dry-run default (S16)."""

from __future__ import annotations

import math
import time
import uuid
from typing import Any

from trendalgo.exchanges.private_client import ccxt_client
from trendalgo.exchanges.registry import ExchangeEntry
from trendalgo.trading.exchange_market import precise_amount
from trendalgo.trading.order_journal import new_client_id
from trendalgo.trading.order_journal_store import default_journal
from trendalgo.trading.order_send import send_market_order
from trendalgo.trading.reconcile import ensure_clear_for_buy
from trendalgo.trading.sizing import (
    OrderSizingError,
    base_amount_from_usd,
    check_ticker_fresh,
    mid_price,
)


class GenericCcxtTradingAdapter:
    """Spot order adapter for any registry exchange with trading_enabled."""

    def __init__(self, entry: ExchangeEntry) -> None:
        self.entry = entry
        self.exchange_id = entry.id

    def _client(self) -> Any:
        return ccxt_client(self.entry)

    def reference_price(self, pair: str) -> float:
        """Last trade price, or the bid/ask mid. Raises when stale or unusable (E1)."""
        ticker = self._client().fetch_ticker(pair)
        check_ticker_fresh(ticker.get("timestamp"), time.time() * 1000)
        for value in (ticker.get("last"), mid_price(ticker)):
            if value is not None and math.isfinite(value) and value > 0:
                return float(value)
        raise OrderSizingError(f"{self.exchange_id}: no usable ticker price for {pair}")

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
        journal = default_journal()
        exchange = self._client()
        with exchange.guard():  # one order flow at a time per key (E8)
            if side == "buy":
                ensure_clear_for_buy(journal, exchange, self.exchange_id, pair)  # E3
            base = base_amount_from_usd(amount_usd, price)
            amount = precise_amount(exchange, pair, base, price)
            client_id = new_client_id()
            journal.record_intent(client_id, self.exchange_id, pair, side, amount)
            order = send_market_order(
                exchange, journal, self.exchange_id, client_id, pair, side, amount
            )
        return {
            "exchange": self.exchange_id,
            "pair": pair,
            "side": side,
            "amount_usd": round(amount_usd, 2),
            "amount": amount,
            "price": price,
            "mode": "live",
            "status": str(order.get("status", "submitted")),
            "order_id": str(order.get("id", "")),
            "client_id": client_id,
        }
