"""Forager TTL cache + synthetic path."""

from __future__ import annotations

import trendalgo.scanner.forager as forager


def test_forager_cache_hit(monkeypatch) -> None:
    monkeypatch.setenv("TRENDALGO_MARKET_SOURCE", "synthetic")
    monkeypatch.setenv("TRENDALGO_FORAGER_CACHE_TTL_S", "60")
    forager._CACHE = None
    forager._CACHE_AT = 0.0
    first = forager.forage_pairs(top_n=3)
    assert first["pair_count"] >= 1
    second = forager.forage_pairs(top_n=3)
    assert second["generated_at"] == first["generated_at"]
    third = forager.forage_pairs(top_n=3, force_refresh=True)
    assert third["pair_count"] >= 1


def test_forager_cache_disabled(monkeypatch) -> None:
    monkeypatch.setenv("TRENDALGO_MARKET_SOURCE", "synthetic")
    monkeypatch.setenv("TRENDALGO_FORAGER_CACHE_TTL_S", "0")
    forager._CACHE = None
    a = forager.forage_pairs(top_n=2)
    b = forager.forage_pairs(top_n=2)
    assert a["pair_count"] >= 1 and b["pair_count"] >= 1


def test_forager_invalid_ttl_and_live_path(monkeypatch) -> None:
    monkeypatch.delenv("TRENDALGO_MARKET_SOURCE", raising=False)
    monkeypatch.setenv("TRENDALGO_FORAGER_CACHE_TTL_S", "nope")
    forager._CACHE = None

    class Row:
        pair = "BTC/USD"
        gain_pct = 0.05
        volume_usd = 5_000_000.0

    monkeypatch.setattr(forager, "verify_kraken_listings", lambda: ["BTC/USD", "ETH/USD"])
    monkeypatch.setattr(forager, "fetch_live_market", lambda pairs: [Row()])
    out = forager.forage_pairs(top_n=2, force_refresh=True)
    assert out["pair_count"] == 1
    assert out["pairs"][0]["pair"] == "BTC/USD"
    assert out["degraded"] is False


def test_forager_live_fallback(monkeypatch) -> None:
    monkeypatch.delenv("TRENDALGO_MARKET_SOURCE", raising=False)
    monkeypatch.setenv("TRENDALGO_FORAGER_CACHE_TTL_S", "0")
    forager._CACHE = None
    monkeypatch.setattr(forager, "verify_kraken_listings", lambda: ["BTC/USD"])
    monkeypatch.setattr(
        forager,
        "fetch_live_market",
        lambda pairs: (_ for _ in ()).throw(RuntimeError("net")),
    )
    out = forager.forage_pairs(top_n=2, force_refresh=True)
    assert out["pair_count"] >= 1
    assert out["degraded"] is True
