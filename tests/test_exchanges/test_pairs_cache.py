"""Pairs list serves static/cache immediately; refreshes in background."""

from __future__ import annotations

import time

import pytest

import trendalgo.exchanges.pairs as pairs_mod


@pytest.fixture(autouse=True)
def _clear_pairs_cache() -> None:
    pairs_mod._CACHE.clear()
    pairs_mod._REFRESHING.clear()
    yield
    pairs_mod._CACHE.clear()
    pairs_mod._REFRESHING.clear()


def test_list_pairs_returns_static_without_blocking(monkeypatch) -> None:
    monkeypatch.setenv("TRENDALGO_PAIRS_CACHE_TTL_S", "3600")
    called = {"n": 0}

    def slow_fetch(exchange_id: str) -> list[str]:
        called["n"] += 1
        time.sleep(0.2)
        return ["AAA/USD", "BBB/USD"] + [f"X{i}/USD" for i in range(10)]

    monkeypatch.setattr(pairs_mod, "_fetch_live_pairs", slow_fetch)
    t0 = time.perf_counter()
    out = pairs_mod.list_pairs_for_exchange("kraken")
    elapsed = time.perf_counter() - t0
    assert elapsed < 0.15
    assert "BTC/USD" in out
    deadline = time.time() + 2
    while called["n"] < 1 and time.time() < deadline:
        time.sleep(0.05)
    assert called["n"] >= 1
    deadline = time.time() + 2
    while "AAA/USD" not in pairs_mod._CACHE.get("kraken", (0, []))[1] and time.time() < deadline:
        time.sleep(0.05)
    cached = pairs_mod.list_pairs_for_exchange("kraken")
    assert "AAA/USD" in cached


def test_force_refresh_sync(monkeypatch) -> None:
    monkeypatch.setenv("TRENDALGO_PAIRS_CACHE_TTL_S", "3600")
    monkeypatch.setattr(
        pairs_mod,
        "_fetch_live_pairs",
        lambda _e: ["ZZZ/USD"] + [f"Y{i}/USD" for i in range(10)],
    )
    out = pairs_mod.list_pairs_for_exchange("kraken", force_refresh=True)
    assert out[0] == "Y0/USD" or "ZZZ/USD" in out
