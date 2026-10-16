"""Staged live-market fetch: volume → gain → 5m; soft-fail per pair."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from trendalgo.market.types import OhlcvPoint
from trendalgo.scanner.live_market import fetch_live_market


@pytest.fixture(autouse=True)
def _disable_ticker_prefilter(monkeypatch: pytest.MonkeyPatch) -> None:
    """OHLCV-stage tests stub candles; skip live ticker prune unless a test overrides it."""
    monkeypatch.setattr(
        "trendalgo.scanner.live_market.fetch_quote_volumes",
        lambda pairs, **_k: {},
    )


def _bars(n: int = 35) -> list[OhlcvPoint]:
    base = int(datetime(2026, 1, 1, tzinfo=UTC).timestamp())
    # Use hourly spacing so extended 1h lookbacks stay consistent in tests.
    step = 3600
    return [
        OhlcvPoint(
            time=base + i * step,
            open=100.0 + i,
            high=101.0 + i,
            low=99.0 + i,
            close=100.5 + i,
            volume=10_000.0,
        )
        for i in range(n)
    ]


def test_fetch_live_market_parallel(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRENDALGO_LIVE_MARKET_WORKERS", "3")

    def fake_fetch(pair: str, timeframe: str, *_a, **_k):
        if pair == "BAD/USD":
            raise RuntimeError("boom")
        n = 35 if timeframe == "1d" else 180 if timeframe == "1h" else 25
        return _bars(n)

    monkeypatch.setattr("trendalgo.scanner.live_market.fetch_ohlcv", fake_fetch)
    rows = fetch_live_market(["SOL/USD", "BAD/USD", "DOT/USD"])
    assert [r.pair for r in rows] == ["SOL/USD", "DOT/USD"]
    assert rows[0].gain_pct != 0
    assert rows[0].bars


def test_fetch_live_market_all_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "trendalgo.scanner.live_market.fetch_ohlcv",
        lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("down")),
    )
    with pytest.raises(RuntimeError, match="live OHLCV"):
        fetch_live_market(["X/USD"], max_retries=1, backoff_seconds=0)


def test_ticker_prefilter_drops_low_volume_before_ohlcv(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def fake_fetch(pair: str, timeframe: str, *_a, **_k):
        calls.append(f"{pair}:{timeframe}")
        return _bars(180)

    monkeypatch.setattr("trendalgo.scanner.live_market.fetch_ohlcv", fake_fetch)
    monkeypatch.setattr(
        "trendalgo.scanner.live_market.fetch_quote_volumes",
        lambda pairs, **_k: {"SOL/USD": 50.0, "BTC/USD": 5_000_000.0},
    )
    rows = fetch_live_market(
        ["SOL/USD", "BTC/USD"],
        min_volume_usd=1_000_000,
        min_gain_pct=0.0,
    )
    assert [r.pair for r in rows] == ["BTC/USD"]
    assert not any(c.startswith("SOL/USD:") for c in calls)
    assert any(c.startswith("BTC/USD:1h") for c in calls)


def test_volume_floor_skips_gain_and_five_minute(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def fake_fetch(pair: str, timeframe: str, *_a, **_k):
        calls.append(f"{pair}:{timeframe}")
        n = 35 if timeframe == "1d" else 180 if timeframe == "1h" else 25
        return _bars(n)

    monkeypatch.setattr("trendalgo.scanner.live_market.fetch_ohlcv", fake_fetch)
    rows = fetch_live_market(
        ["SOL/USD"],
        min_volume_usd=10**18,
        min_gain_pct=0.0,
    )
    assert rows == []
    assert any(c.endswith(":1h") for c in calls)
    assert not any(c.endswith(":1d") for c in calls)
    assert not any(c.endswith(":5m") for c in calls)


def test_gain_floor_skips_five_minute_after_volume_pass(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def fake_fetch(pair: str, timeframe: str, *_a, **_k):
        calls.append(f"{pair}:{timeframe}")
        if timeframe == "1d":
            # Flat closes → ~0% gain so a positive floor excludes the pair.
            bars = _bars(35)
            flat = [
                OhlcvPoint(
                    time=b.time,
                    open=100.0,
                    high=100.0,
                    low=100.0,
                    close=100.0,
                    volume=b.volume,
                )
                for b in bars
            ]
            return flat
        n = 180 if timeframe == "1h" else 25
        return _bars(n)

    monkeypatch.setattr("trendalgo.scanner.live_market.fetch_ohlcv", fake_fetch)
    rows = fetch_live_market(
        ["SOL/USD"],
        min_volume_usd=0.0,
        min_gain_pct=0.5,
    )
    assert rows == []
    assert any(c.endswith(":1h") for c in calls)
    assert any(c.endswith(":1d") for c in calls)
    assert not any(c.endswith(":5m") for c in calls)


def test_full_pass_fetches_volume_then_gain_then_five_m(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    order: list[str] = []

    def fake_fetch(pair: str, timeframe: str, *_a, **_k):
        order.append(timeframe)
        n = 35 if timeframe == "1d" else 180 if timeframe == "1h" else 25
        return _bars(n)

    monkeypatch.setattr("trendalgo.scanner.live_market.fetch_ohlcv", fake_fetch)
    rows = fetch_live_market(["SOL/USD"], min_volume_usd=0.0, min_gain_pct=0.0)
    assert len(rows) == 1
    assert order == ["1h", "1d", "5m"]


def test_gain7d_floor_skips_daily_and_five_m(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def fake_fetch(pair: str, timeframe: str, *_a, **_k):
        calls.append(f"{pair}:{timeframe}")
        # Flat 1h closes → ~0% 7d gain.
        if timeframe == "1h":
            bars = _bars(180)
            return [
                OhlcvPoint(
                    time=b.time,
                    open=100.0,
                    high=100.0,
                    low=100.0,
                    close=100.0,
                    volume=10_000.0,
                )
                for b in bars
            ]
        return _bars(35 if timeframe == "1d" else 25)

    monkeypatch.setattr("trendalgo.scanner.live_market.fetch_ohlcv", fake_fetch)
    rows = fetch_live_market(
        ["SOL/USD"],
        min_volume_usd=0.0,
        min_gain_pct=0.0,
        min_gain_7d_pct=0.05,
    )
    assert rows == []
    assert any(c.endswith(":1h") for c in calls)
    assert not any(c.endswith(":1d") for c in calls)
    assert not any(c.endswith(":5m") for c in calls)
