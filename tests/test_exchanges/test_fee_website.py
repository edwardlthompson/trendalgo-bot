"""Tests for public fee-page fetch."""

from unittest.mock import patch

from trendalgo.exchanges.fee_website import fetch_website_fees


def test_fetch_website_fees_verified_seed() -> None:
    seed = {
        "taker_pct": 0.0001,
        "maker_pct": 0.0,
        "source_url": "https://www.binance.us/fees",
    }
    html = "Binance.US offers 0% maker fees and 0.01% taker fees for all customers"
    with patch("trendalgo.exchanges.fee_website.fetch_fee_page", return_value=html):
        live = fetch_website_fees("binanceus", seed)
    assert live.taker_pct == 0.0001
    assert live.source == "website_verified"
    assert live.verified is True


def test_fetch_website_fees_alternate_url() -> None:
    seed = {
        "taker_pct": 0.006,
        "maker_pct": 0.004,
        "source_url": "https://help.coinbase.com/en/coinbase/trading-and-funding/advanced-trade/advanced-trade-fees",
        "alternate_urls": [
            "https://help.coinbase.com/en/exchange/trading-and-funding/exchange-fees"
        ],
    }
    primary = "Fees vary by order type with no published percentages."
    alternate = "Tier Taker Fee Maker Fee $0K-$10K 60bps 40bps"

    def fake_fetch(url: str) -> str:
        if "exchange-fees" in url:
            return alternate
        return primary

    with patch("trendalgo.exchanges.fee_website.fetch_fee_page", side_effect=fake_fetch):
        live = fetch_website_fees("coinbaseadvanced", seed)
    assert live.taker_pct == 0.006
    assert live.source == "website_verified"


def test_fetch_website_fees_parsed() -> None:
    seed = {
        "taker_pct": 0.004,
        "maker_pct": 0.002,
        "source_url": "https://www.gemini.com/fees",
    }
    html = "<p>Taker 0.50%</p><p>Maker 0.25%</p>"
    with patch("trendalgo.exchanges.fee_website.fetch_fee_page", return_value=html):
        live = fetch_website_fees("gemini", seed)
    assert live.taker_pct == 0.005
    assert live.source == "website"
