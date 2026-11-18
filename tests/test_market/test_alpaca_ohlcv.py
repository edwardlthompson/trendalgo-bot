"""TF-P5: Alpaca OHLCV provider keyed vs synthetic."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

from trendalgo.market.alpaca_ohlcv import (
    AlpacaOhlcvProvider,
    fetch_alpaca_equity_bars,
    fetch_alpaca_equity_bars_multi,
    normalize_alpaca_symbol,
)


def test_normalize_alpaca_symbol() -> None:
    assert normalize_alpaca_symbol("aapl/usd") == "AAPL"
    assert normalize_alpaca_symbol("MSFT") == "MSFT"


def test_provider_synthetic_without_keys(monkeypatch: Any) -> None:
    monkeypatch.delenv("ALPACA_API_KEY", raising=False)
    monkeypatch.delenv("ALPACA_API_SECRET", raising=False)
    monkeypatch.setattr(
        "trendalgo.market.alpaca_ohlcv.alpaca_credentials",
        lambda: None,
    )
    eng = AlpacaOhlcvProvider()
    until = datetime.now(UTC)
    since = until - timedelta(days=5)
    points = eng.fetch("alpaca", "AAPL", "1d", since, until)
    assert len(points) >= 1
    assert eng.last_source == "synthetic"


def test_fetch_alpaca_equity_bars_mock() -> None:
    until = datetime(2026, 3, 10, tzinfo=UTC)
    since = until - timedelta(days=3)
    payload = {
        "bars": [
            {
                "t": "2026-03-09T05:00:00Z",
                "o": 100,
                "h": 110,
                "l": 99,
                "c": 105,
                "v": 1000,
            }
        ]
    }

    class _Resp:
        def read(self) -> bytes:
            return json.dumps(payload).encode()

        def __enter__(self) -> _Resp:
            return self

        def __exit__(self, *args: object) -> None:
            return None

    def _open(req: object, timeout: float = 0) -> _Resp:
        _ = req, timeout
        return _Resp()

    points = fetch_alpaca_equity_bars(
        "AAPL",
        "1d",
        since,
        until,
        credentials=("k", "s"),
        opener=_open,
    )
    assert len(points) == 1
    assert points[0].close == 105.0


def test_fetch_alpaca_equity_bars_multi_mock() -> None:
    until = datetime(2026, 3, 10, tzinfo=UTC)
    since = until - timedelta(days=3)
    payload = {
        "bars": {
            "AAPL": [
                {
                    "t": "2026-03-09T05:00:00Z",
                    "o": 100,
                    "h": 110,
                    "l": 99,
                    "c": 105,
                    "v": 1000,
                }
            ],
            "MSFT": [
                {
                    "t": "2026-03-09T05:00:00Z",
                    "o": 200,
                    "h": 210,
                    "l": 199,
                    "c": 205,
                    "v": 2000,
                }
            ],
        }
    }

    class _Resp:
        def read(self) -> bytes:
            return json.dumps(payload).encode()

        def __enter__(self) -> _Resp:
            return self

        def __exit__(self, *args: object) -> None:
            return None

    def _open(req: object, timeout: float = 0) -> _Resp:
        _ = req, timeout
        return _Resp()

    out = fetch_alpaca_equity_bars_multi(
        ["AAPL", "MSFT"],
        "1d",
        since,
        until,
        credentials=("k", "s"),
        opener=_open,
    )
    assert set(out) == {"AAPL", "MSFT"}
    assert out["AAPL"][0].close == 105.0
    assert out["MSFT"][0].volume == 2000.0


def test_fetch_multi_on_chunk_callback() -> None:
    until = datetime(2026, 3, 10, tzinfo=UTC)
    since = until - timedelta(days=1)
    calls: list[tuple[int, int, str]] = []

    class _Resp:
        def read(self) -> bytes:
            return json.dumps({"bars": {"AAA": [], "BBB": []}}).encode()

        def __enter__(self) -> _Resp:
            return self

        def __exit__(self, *args: object) -> None:
            return None

    def _open(req: object, timeout: float = 0) -> _Resp:
        _ = req, timeout
        return _Resp()

    fetch_alpaca_equity_bars_multi(
        ["AAA", "BBB"],
        "1d",
        since,
        until,
        credentials=("k", "s"),
        opener=_open,
        chunk_size=1,
        max_calls_per_min=10_000,
        on_chunk=lambda d, t, s: calls.append((d, t, s)),
    )
    assert calls == [(1, 2, "AAA"), (2, 2, "BBB")]
