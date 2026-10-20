"""Direct CoinGecko / CMC listing URLs (API id paths, not search pages)."""

from __future__ import annotations

import pytest

from trendalgo.device.coin_listing import coin_listing_url
from trendalgo.device.coingecko_ids import resolve_coingecko_id


def test_coin_listing_prefers_cmc_slug() -> None:
    assert "currencies/bitcoin" in coin_listing_url({"cmc_slug": "bitcoin", "symbol": "BTC"})


def test_coin_listing_direct_cg_api_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRENDALGO_OFFLINE", "1")
    eth = coin_listing_url({"symbol": "ETH", "slug": "eth", "cg_id": "eth"})
    assert eth == "https://www.coingecko.com/en/coins/ethereum"
    avax = coin_listing_url({"symbol": "AVAX", "slug": "avax"})
    assert avax == "https://www.coingecko.com/en/coins/avalanche-2"
    assert "%2D" not in avax
    hype = coin_listing_url({"symbol": "HYPE", "slug": "hype"})
    assert hype == "https://www.coingecko.com/en/coins/hyperliquid"
    # Never a search page.
    assert "/search" not in eth
    assert "/search" not in hype


def test_resolve_uses_bootstrap_map(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRENDALGO_OFFLINE", "1")
    assert resolve_coingecko_id("BTC", allow_network=False) == "bitcoin"
    assert resolve_coingecko_id("ETH/USD", allow_network=False) == "ethereum"
    assert resolve_coingecko_id("AVAX", allow_network=False) == "avalanche-2"


def test_unknown_offline_has_no_search_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRENDALGO_OFFLINE", "1")
    url = coin_listing_url({"symbol": "ZZZNOPE", "slug": "zzznope"})
    assert url == ""
    assert "/search" not in url
