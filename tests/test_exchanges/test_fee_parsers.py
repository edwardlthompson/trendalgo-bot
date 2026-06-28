"""Tests for fee page HTML parsers."""

from trendalgo.exchanges.fee_parsers import (
    fees_verified_on_page,
    parse_fees_from_html,
    pct_variants,
)


def test_pct_variants_kraken() -> None:
    assert "0.26%" in pct_variants(0.0026)
    assert "0,26%" in pct_variants(0.0026)
    assert "0.16%" in pct_variants(0.0016)


def test_fees_verified_on_page() -> None:
    html = "<p>Spot taker fee 0.45% and maker fee 0.35% for retail users</p>"
    assert fees_verified_on_page(html, 0.0045, 0.0035)


def test_fees_verified_kraken_comma_decimal() -> None:
    html = "<span>Spot taker 0,26% and maker 0.16%</span>"
    assert fees_verified_on_page(html, 0.0026, 0.0016)


def test_parse_binanceus_promo_html() -> None:
    html = "Binance.US offers 0% maker fees and 0.01% taker fees for all customers"
    parsed = parse_fees_from_html("binanceus", html)
    assert parsed == (0.0001, 0.0)


def test_parse_binanceus_legacy_html() -> None:
    html = "Spot trading fees Taker 0.45% Maker 0.35% for standard accounts"
    parsed = parse_fees_from_html("binanceus", html)
    assert parsed == (0.0045, 0.0035)


def test_parse_coinbase_bps_html() -> None:
    html = "Tier Taker Fee Maker Fee $0K-$10K 60bps 40bps $10K-$50K 40bps 25bps"
    parsed = parse_fees_from_html("coinbaseadvanced", html)
    assert parsed == (0.006, 0.004)


def test_parse_okx_embedded_json() -> None:
    html = '{"lowerTradeVolume":0,"makerFee":0.002,"takerFee":0.0035,"upperTradeVolume":10000}'
    parsed = parse_fees_from_html("okx", html)
    assert parsed == (0.0035, 0.002)


def test_parse_gemini_spot_table() -> None:
    html = "Spot maker fees taker fees 0.600% 1.200% ≥ $0 ≥ $0"
    parsed = parse_fees_from_html("gemini", html)
    assert parsed == (0.012, 0.006)


def test_parse_generic_labeled() -> None:
    html = "<div>Taker fee 0.40%</div><div>Maker fee 0.20%</div>"
    parsed = parse_fees_from_html("unknown", html)
    assert parsed == (0.004, 0.002)
