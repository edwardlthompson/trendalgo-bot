"""The one symbol mapper for candles, signals, and orders (S14, E4).

Every path that turns a user symbol into a venue pair goes through normalize_pair, so a candle
request and an order for the same symbol always name the same market.
"""

from __future__ import annotations

from trendalgo.exchanges.registry import ExchangeEntry, get_entry


def quote_currency(entry: ExchangeEntry | str) -> str:
    """Preferred quote currency for an exchange (USD for US venues, USDT common elsewhere)."""
    if isinstance(entry, str):
        entry = get_entry(entry)
    return getattr(entry, "quote_currency", "USD")


def _base(pair_or_symbol: str) -> str:
    raw = pair_or_symbol.strip().upper()
    for separator in ("/", "-"):
        if separator in raw:
            return raw.split(separator, 1)[0]
    if raw.endswith("USD") and len(raw) > 3:
        return raw[:-3]
    return raw


def normalize_pair(pair_or_symbol: str, exchange_id: str) -> str:
    """Return BASE/QUOTE for a venue, where QUOTE is that venue's quote currency.

    Accepts BTC, BTC/USD, BTC-USD, and BTCUSD. The quote is always the venue's: a BTC/USDT
    request on Kraken becomes BTC/USD, as orders always did.
    """
    base = _base(pair_or_symbol)
    if not base:
        raise ValueError(f"no base asset in {pair_or_symbol!r}")
    return f"{base}/{quote_currency(exchange_id)}"


def to_ccxt_pair(base: str, exchange_id: str) -> str:
    """Build the CCXT pair string for a base asset on a given exchange."""
    return normalize_pair(base, exchange_id)
