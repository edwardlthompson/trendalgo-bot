"""Trading adapter registry — maps exchange id → adapter instance."""

from __future__ import annotations

from trendalgo.exchanges.registry import get_entry, list_trading_exchanges
from trendalgo.trading.runner.adapters.generic import GenericCcxtTradingAdapter


def get_trading_adapter(exchange_id: str) -> GenericCcxtTradingAdapter:
    entry = get_entry(exchange_id)
    if not entry.trading_enabled:
        raise KeyError(f"exchange not enabled for trading: {exchange_id}")
    return GenericCcxtTradingAdapter(entry)


def list_trading_adapter_ids() -> list[str]:
    return [e.id for e in list_trading_exchanges()]
