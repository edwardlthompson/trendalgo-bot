"""CoinGecko/Kraken OHLCV shim — synthetic returns must differ by coin."""

from __future__ import annotations

import pytest

from trendalgo.lts_vendor.shims import api_coingecko as cg


def test_synthetic_hourly_returns_differ_by_coin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRENDALGO_MARKET_SOURCE", "synthetic")
    monkeypatch.setattr(cg, "fetch_kraken_hourly_rows", lambda *_a, **_k: None)
    client = cg.CoinGeckoClient()
    a = client.get_hourly_ohlcv("avax", days=30, symbol="AVAX")
    b = client.get_hourly_ohlcv("sui", days=30, symbol="SUI")
    assert a and b
    ret_a = float(a[-1]["close"]) / float(a[0]["close"]) - 1.0
    ret_b = float(b[-1]["close"]) / float(b[0]["close"]) - 1.0
    assert abs(ret_a - ret_b) > 1e-4


def test_pair_candidates_prefer_symbol() -> None:
    assert cg._pair_candidates("bitcoin", "BTC")[0] == "BTC/USD"
    assert "AVAX/USD" in cg._pair_candidates("avax", "AVAX")


def test_synthetic_rows_are_flagged_so_the_cache_never_persists_them(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TRENDALGO_MARKET_SOURCE", "synthetic")
    monkeypatch.setattr(cg, "fetch_kraken_hourly_rows", lambda *_a, **_k: None)
    rows = cg.CoinGeckoClient().get_hourly_ohlcv("avax", days=30, symbol="AVAX")
    assert rows
    assert all(row.get("synthetic") is True for row in rows)


def test_exchange_rows_are_not_flagged_synthetic(monkeypatch: pytest.MonkeyPatch) -> None:
    kraken_rows = [{"ts": 1.0, "open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0, "volume": 1.0}]
    monkeypatch.setattr(cg, "fetch_kraken_hourly_rows", lambda *_a, **_k: kraken_rows)
    rows = cg.CoinGeckoClient().get_hourly_ohlcv("avax", days=30, symbol="AVAX")
    assert rows == kraken_rows
    assert not any(row.get("synthetic") for row in rows or [])


def _no_kraken_and_no_forced_synthetic(monkeypatch: pytest.MonkeyPatch) -> None:
    """Conftest forces TRENDALGO_MARKET_SOURCE=synthetic; clear it so the flag decides."""
    monkeypatch.delenv("TRENDALGO_MARKET_SOURCE", raising=False)
    monkeypatch.setattr(cg, "fetch_kraken_hourly_rows", lambda *_a, **_k: None)


def test_synthetic_fallback_is_off_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    _no_kraken_and_no_forced_synthetic(monkeypatch)
    monkeypatch.delenv("BACKTEST_ALLOW_SYNTHETIC", raising=False)
    assert cg.CoinGeckoClient().get_hourly_ohlcv("avax", days=30, symbol="AVAX") is None


@pytest.mark.parametrize("flag", ["1", "true", "YES", " on "])
def test_synthetic_fallback_opts_in_with_flag(monkeypatch: pytest.MonkeyPatch, flag: str) -> None:
    _no_kraken_and_no_forced_synthetic(monkeypatch)
    monkeypatch.setenv("BACKTEST_ALLOW_SYNTHETIC", flag)
    rows = cg.CoinGeckoClient().get_hourly_ohlcv("avax", days=30, symbol="AVAX")
    assert rows
    assert all(row.get("synthetic") is True for row in rows)


@pytest.mark.parametrize("flag", ["0", "", "maybe", "off"])
def test_synthetic_fallback_stays_off_for_other_values(
    monkeypatch: pytest.MonkeyPatch, flag: str
) -> None:
    _no_kraken_and_no_forced_synthetic(monkeypatch)
    monkeypatch.setenv("BACKTEST_ALLOW_SYNTHETIC", flag)
    assert cg.CoinGeckoClient().get_hourly_ohlcv("avax", days=30, symbol="AVAX") is None
