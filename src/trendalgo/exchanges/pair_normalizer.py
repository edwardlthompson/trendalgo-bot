"""Pair normalization per exchange (S14)."""

from __future__ import annotations

from trendalgo.exchanges.registry import ExchangeEntry, get_entry


def quote_currency(entry: ExchangeEntry | str) -> str:
    """Preferred quote currency for an exchange (USD for US venues, USDT common elsewhere)."""
    if isinstance(entry, str):
        entry = get_entry(entry)
    return getattr(entry, "quote_currency", "USD")


def to_ccxt_pair(base: str, exchange_id: str) -> str:
    """Build CCXT pair string for a base asset on a given exchange."""
    base_norm = base.upper()
    quote = quote_currency(exchange_id)
    return f"{base_norm}/{quote}"


def normalize_pair(pair: str, exchange_id: str) -> str:
    """Normalize user pair input to exchange-preferred quote (BTC/USD → BTC/USDT on Binance)."""
    parts = pair.upper().split("/")
    if len(parts) != 2:
        return pair.upper()
    base, _quote = parts[0], parts[1]
    return to_ccxt_pair(base, exchange_id)
