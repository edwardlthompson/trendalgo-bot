"""Stress portfolio fixture tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from trendalgo.market.top100 import Top100Asset
from trendalgo.portfolio.db import PortfolioStore
from trendalgo.portfolio.multi_exchange import aggregate_holdings
from trendalgo.portfolio.stress_fixture import (
    apply_stress_portfolio,
    generate_stress_holdings,
    load_or_build_stress_cache,
)


def _fake_universe(n: int = 100) -> list[Top100Asset]:
    return [
        Top100Asset(symbol=f"T{i}", name=f"Token {i}", price_usd=1.0 + i, market_cap_rank=i + 1)
        for i in range(n)
    ]


def test_generate_stress_holdings_distributes_across_exchanges() -> None:
    exchanges = ["kraken", "binanceus", "binance"]
    holdings = generate_stress_holdings(_fake_universe(), exchanges, seed=7)
    assert set(holdings) == set(exchanges)
    assert sum(len(v) for v in holdings.values()) > len(exchanges) * 10


def test_apply_stress_portfolio(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRENDALGO_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TRENDALGO_STRESS_PORTFOLIO", "1")

    def _fake_fetch() -> list[Top100Asset]:
        return _fake_universe(100)

    monkeypatch.setattr(
        "trendalgo.portfolio.stress_fixture.fetch_top100_universe",
        _fake_fetch,
    )
    store = PortfolioStore(tmp_path / "portfolio.db")
    result = apply_stress_portfolio(store, seed=99, refresh_prices=True)
    assert result["exchange_count"] >= 9
    assert result["unique_assets"] >= 50
    agg = aggregate_holdings(store)
    assert len(agg["holdings"]) >= 50
    assert float(agg["total_usd"]) > 100_000


def test_stress_cache_reuse(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRENDALGO_DATA_DIR", str(tmp_path))
    calls = {"n": 0}

    def _fake_fetch() -> list[Top100Asset]:
        calls["n"] += 1
        return _fake_universe(100)

    monkeypatch.setattr(
        "trendalgo.portfolio.stress_fixture.fetch_top100_universe",
        _fake_fetch,
    )
    load_or_build_stress_cache(seed=1, refresh=True)
    load_or_build_stress_cache(seed=1, refresh=False)
    assert calls["n"] == 1
