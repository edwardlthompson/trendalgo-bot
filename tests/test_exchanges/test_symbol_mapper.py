"""One symbol mapper (E4): candles and orders name the same venue pair for every symbol."""

from __future__ import annotations

import pytest

from trendalgo.exchanges.pair_normalizer import normalize_pair, to_ccxt_pair
from trendalgo.market.kraken import KRAKEN_PAIR, kraken_pair


@pytest.mark.parametrize(("symbol", "pair"), sorted(KRAKEN_PAIR.items()))
def test_each_plan_symbol_round_trips_to_its_kraken_pair(symbol: str, pair: str) -> None:
    assert kraken_pair(symbol) == pair == normalize_pair(symbol, "kraken")
    assert normalize_pair(pair, "kraken") == pair
    assert normalize_pair(f"{symbol}-USD", "kraken") == pair
    assert normalize_pair(f"{symbol}USD", "kraken") == pair
    assert normalize_pair(symbol.lower(), "kraken") == pair


def test_a_bare_symbol_no_longer_passes_through_unchanged() -> None:
    # Regression (E4): the old mapper sent "BTC" to Kraken as-is, which Kraken rejects.
    assert normalize_pair("BTC", "kraken") == "BTC/USD"
    assert to_ccxt_pair("btc", "kraken") == "BTC/USD"
    assert kraken_pair("LTC") == "LTC/USD"


def test_the_venue_quote_always_wins() -> None:
    assert normalize_pair("BTC/USDT", "kraken") == "BTC/USD"
    assert normalize_pair("BTC/USD", "binance") == "BTC/USDT"


def test_an_empty_symbol_is_rejected() -> None:
    with pytest.raises(ValueError, match="no base asset"):
        normalize_pair("  ", "kraken")
