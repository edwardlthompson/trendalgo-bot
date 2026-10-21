"""Kraken ticker volumes: per-base USD aggregation across quotes."""

from __future__ import annotations

from trendalgo.market.kraken import (
    _aggregate_base_volumes_usd,
    fetch_quote_volumes,
    resolve_kraken_market,
)


def test_resolve_kraken_market_keeps_explicit_quote() -> None:
    assert resolve_kraken_market("SOL/EUR") == "SOL/EUR"
    assert resolve_kraken_market("sol/usdt") == "SOL/USDT"
    assert resolve_kraken_market("BTC") == "BTC/USD"


def test_aggregate_sums_usd_and_converted_eur(monkeypatch) -> None:
    raw = {
        "AAA/USD": {"quoteVolume": 800_000.0, "last": 1.0, "baseVolume": 800_000.0},
        "AAA/EUR": {"quoteVolume": 200_000.0, "last": 2.0, "baseVolume": 100_000.0},
        "EUR/USD": {"last": 1.10, "quoteVolume": 1.0, "baseVolume": 1.0},
        "BBB/USDT": {"quoteVolume": 50_000.0, "last": 1.0, "baseVolume": 50_000.0},
    }
    by_base = _aggregate_base_volumes_usd(raw)
    # 800k USD + 200k EUR * 1.10 = 1_020_000
    assert by_base["AAA"] == 800_000.0 + 200_000.0 * 1.10
    assert by_base["BBB"] == 50_000.0


def test_fetch_quote_volumes_maps_canonical_pairs(monkeypatch) -> None:
    raw = {
        "SOL/USD": {"quoteVolume": 1_000_000.0, "last": 100.0, "baseVolume": 10_000.0},
        "SOL/EUR": {"quoteVolume": 500_000.0, "last": 90.0, "baseVolume": 5_000.0},
        "EUR/USD": {"last": 1.0, "quoteVolume": 1.0, "baseVolume": 1.0},
        "ETH/USD": {"quoteVolume": 2_000_000.0, "last": 2000.0, "baseVolume": 1000.0},
    }

    class _Client:
        def fetch_tickers(self) -> dict:
            return raw

    monkeypatch.setattr("trendalgo.market.kraken._client", lambda timeout_ms=10_000: _Client())
    monkeypatch.setattr(
        "trendalgo.market.kraken.call_with_backoff",
        lambda fn, **_k: fn(),
    )
    got = fetch_quote_volumes(["SOL/USD", "ETH/USD", "MISSING/USD"])
    assert got["SOL/USD"] == 1_500_000.0
    assert got["ETH/USD"] == 2_000_000.0
    assert "MISSING/USD" not in got
