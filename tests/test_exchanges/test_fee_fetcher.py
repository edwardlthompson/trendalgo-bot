"""Tests for fee fetch helpers."""

from trendalgo.exchanges.fee_fetcher import fetch_ccxt_fees, retail_fees_from_trading


def test_retail_fees_from_tier_table() -> None:
    trading = {
        "taker": 0.012,
        "maker": 0.006,
        "tiers": {
            "taker": [[0.0, 0.006], [10000.0, 0.004]],
            "maker": [[0.0, 0.004], [10000.0, 0.0025]],
        },
    }
    taker, maker = retail_fees_from_trading(trading)
    assert taker == 0.006
    assert maker == 0.004


def test_fetch_ccxt_fees_kraken_optional() -> None:
    """CCXT path kept for future API sync — not used in production fee sync."""
    live = fetch_ccxt_fees("kraken")
    assert live.taker_pct == 0.0026
    assert live.maker_pct == 0.0016
    assert live.source == "ccxt"
