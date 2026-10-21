"""Kraken listings: synthetic default + live-fetch fallback + canonical quotes."""

from __future__ import annotations

import trendalgo.scanner.listings as listings


def test_verify_explicit_pairs() -> None:
    assert listings.verify_kraken_listings(("btc/usdt", "ETH/USD")) == ["BTC/USD", "ETH/USD"]


def test_synthetic_uses_default_universe(monkeypatch) -> None:
    monkeypatch.setenv("TRENDALGO_MARKET_SOURCE", "synthetic")
    listings._CACHE = None
    got = listings.verify_kraken_listings()
    assert "BTC/USD" in got
    assert len(got) >= 5


def test_live_fetch_failure_falls_back(monkeypatch) -> None:
    monkeypatch.delenv("TRENDALGO_MARKET_SOURCE", raising=False)
    listings._CACHE = None

    def boom() -> list[str]:
        raise RuntimeError("offline")

    monkeypatch.setattr(listings, "_fetch_kraken_spot_canonical", boom)
    got = listings.verify_kraken_listings()
    assert got == list(listings.DEFAULT_KRAKEN_SPOT)


def test_live_fetch_uses_full_spot_catalog(monkeypatch) -> None:
    monkeypatch.delenv("TRENDALGO_MARKET_SOURCE", raising=False)
    monkeypatch.delenv("TRENDALGO_SCANNER_MAX_PAIRS", raising=False)
    listings._CACHE = None
    catalog = [f"C{i:03d}/USD" for i in range(40)] + ["BTC/USD", "ETH/EUR"]
    monkeypatch.setattr(listings, "_fetch_kraken_spot_canonical", lambda: list(catalog))
    got = listings.verify_kraken_listings()
    assert len(got) == len(catalog)
    assert "C000/USD" in got
    assert "ETH/EUR" in got
    listings._CACHE = None


def test_live_fetch_respects_max_pairs_cap(monkeypatch) -> None:
    monkeypatch.delenv("TRENDALGO_MARKET_SOURCE", raising=False)
    monkeypatch.setenv("TRENDALGO_SCANNER_MAX_PAIRS", "12")
    listings._CACHE = None
    catalog = [f"C{i:03d}/USD" for i in range(40)]
    monkeypatch.setattr(listings, "_fetch_kraken_spot_canonical", lambda: list(catalog))
    got = listings.verify_kraken_listings()
    assert got == catalog[:12]
    listings._CACHE = None


def test_pick_canonical_pair_prefers_usd_then_usdt_then_eur() -> None:
    assert listings.pick_canonical_pair(["AAA/EUR", "AAA/USDT", "AAA/USD"]) == "AAA/USD"
    assert listings.pick_canonical_pair(["BBB/EUR", "BBB/USDT"]) == "BBB/USDT"
    assert listings.pick_canonical_pair(["CCC/GBP", "CCC/EUR"]) == "CCC/EUR"
    assert listings.pick_canonical_pair(["USD/EUR", "EUR/USD"]) is None
