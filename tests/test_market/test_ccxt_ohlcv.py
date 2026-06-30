"""CCXT OHLCV fetch helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from trendalgo.market import ccxt_ohlcv
from trendalgo.market.types import OhlcvPoint


def test_rows_to_points_filters_and_deduplicates() -> None:
    since = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    until = datetime(2026, 1, 1, 2, 0, tzinfo=UTC)
    t0 = int(since.timestamp()) * 1000
    t1 = int((since.replace(hour=1)).timestamp()) * 1000
    rows = [
        [t0, 1.0, 2.0, 0.5, 1.5, 10.0],
        [t0, 9.0, 9.0, 9.0, 9.0, 9.0],
        [t1, 2.0, 3.0, 1.0, 2.5, 20.0],
    ]
    points = ccxt_ohlcv._rows_to_points(rows, since, until)
    assert len(points) == 2
    assert points[0] == OhlcvPoint(
        time=int(since.timestamp()), open=1.0, high=2.0, low=0.5, close=1.5, volume=10.0
    )


def test_fetch_exchange_ohlcv_paginates(monkeypatch: pytest.MonkeyPatch) -> None:
    since = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    until = datetime(2026, 1, 1, 1, 0, tzinfo=UTC)
    t0 = int(since.timestamp()) * 1000
    t1 = int(until.timestamp()) * 1000
    batches = iter(
        [
            [[t0, 1.0, 2.0, 0.5, 1.5, 10.0]],
            [[t1, 2.0, 3.0, 1.0, 2.5, 20.0]],
        ]
    )

    class FakeExchange:
        def fetch_ohlcv(
            self, _pair: str, _tf: str, since: int | None = None, limit: int = 720
        ) -> list[list[float]]:
            del since, limit
            return next(batches)

    monkeypatch.setattr(
        ccxt_ohlcv,
        "_client",
        lambda _exchange_id: FakeExchange(),
    )
    batches_seen: list[tuple[int, int]] = []

    def on_batch(batch: int, total: int) -> None:
        batches_seen.append((batch, total))

    points = ccxt_ohlcv.fetch_exchange_ohlcv(
        "kraken",
        "BTC/USD",
        "1h",
        since,
        until,
        on_batch=on_batch,
    )
    assert len(points) == 2
    assert batches_seen == [(1, 1), (1, 2)]


def test_fetch_exchange_ohlcv_retries_then_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    since = datetime(2026, 1, 1, tzinfo=UTC)
    until = datetime(2026, 1, 2, tzinfo=UTC)

    class BrokenExchange:
        def fetch_ohlcv(self, *_args: Any, **_kwargs: Any) -> list[list[float]]:
            raise RuntimeError("network down")

    monkeypatch.setattr(ccxt_ohlcv, "_client", lambda _exchange_id: BrokenExchange())
    monkeypatch.setattr(ccxt_ohlcv.time, "sleep", lambda _sec: None)
    with pytest.raises(RuntimeError, match="network down"):
        ccxt_ohlcv.fetch_exchange_ohlcv("kraken", "BTC/USD", "1h", since, until, max_retries=2)
