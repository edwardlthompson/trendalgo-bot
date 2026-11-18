"""FX-AS1: AlgoSpecial H1 parse + D1 derive."""

from __future__ import annotations

import urllib.error
from datetime import UTC, datetime

import pytest

from trendalgo.market.algospecial_forex import (
    AlgoSpecialUnsupportedError,
    derive_daily_from_h1,
    fetch_algospecial_h1,
    parse_algospecial_rows,
    to_algospecial_symbol,
)
from trendalgo.market.types import OhlcvPoint


def test_to_algospecial_symbol() -> None:
    assert to_algospecial_symbol("EUR/USD") == "EURUSD"
    assert to_algospecial_symbol("eurusd") == "EURUSD"


def test_parse_algospecial_rows_dot_timestamp() -> None:
    rows = [
        {
            "Timestamp": "2025.10.01 01:00:00",
            "Open": 1.1,
            "High": 1.2,
            "Low": 1.0,
            "Close": 1.15,
            "TickVolume": 10,
        },
        {
            "Timestamp": "2025.10.01 00:00:00",
            "Open": 1.0,
            "High": 1.05,
            "Low": 0.99,
            "Close": 1.1,
            "TickVolume": 5,
        },
    ]
    points = parse_algospecial_rows(rows)
    assert len(points) == 2
    assert points[0].close == 1.1
    assert points[1].close == 1.15
    assert points[0].time < points[1].time


def test_derive_daily_from_h1() -> None:
    # Two hours same UTC day + one next day.
    t0 = int(datetime(2025, 10, 1, 0, 0, tzinfo=UTC).timestamp())
    t1 = int(datetime(2025, 10, 1, 1, 0, tzinfo=UTC).timestamp())
    t2 = int(datetime(2025, 10, 2, 0, 0, tzinfo=UTC).timestamp())
    hourly = [
        OhlcvPoint(time=t0, open=1.0, high=1.2, low=0.9, close=1.1, volume=2),
        OhlcvPoint(time=t1, open=1.1, high=1.3, low=1.05, close=1.25, volume=3),
        OhlcvPoint(time=t2, open=1.25, high=1.4, low=1.2, close=1.3, volume=4),
    ]
    daily = derive_daily_from_h1(hourly)
    assert len(daily) == 2
    assert daily[0].open == 1.0
    assert daily[0].high == 1.3
    assert daily[0].low == 0.9
    assert daily[0].close == 1.25
    assert daily[0].volume == 5
    assert daily[1].close == 1.3


class _FakeResp:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> _FakeResp:
        return self

    def __exit__(self, *args: object) -> None:
        return None


def test_fetch_algospecial_h1_uses_opener() -> None:
    import trendalgo.market.algospecial_forex as mod

    mod._LAST_GOOD_UNTIL = None
    payload = (
        b'{"data":[{"Timestamp":"2025.10.01 00:00:00","Open":1,"High":1.1,'
        b'"Low":0.9,"Close":1.05,"TickVolume":1}]}'
    )

    def opener(req: object, timeout: float = 0) -> _FakeResp:  # noqa: ARG001
        return _FakeResp(payload)

    since = datetime(2025, 10, 1, tzinfo=UTC)
    until = datetime(2025, 10, 2, tzinfo=UTC)
    points = fetch_algospecial_h1("EUR/USD", since, until, opener=opener)
    assert len(points) == 1
    assert points[0].close == 1.05


def test_fetch_algospecial_h1_walks_back_on_empty() -> None:
    """Wall-clock windows past the free feed return []; walk back until data appears."""
    import trendalgo.market.algospecial_forex as mod

    mod._LAST_GOOD_UNTIL = None
    calls: list[str] = []

    def opener(req: object, timeout: float = 0) -> _FakeResp:  # noqa: ARG001
        url = str(req.full_url)  # type: ignore[attr-defined]
        calls.append(url)
        if "2025-10" in url:
            body = (
                b'{"data":[{"Timestamp":"2025.10.15 00:00:00","Open":1,"High":1.1,'
                b'"Low":0.9,"Close":1.05,"TickVolume":1}]}'
            )
        else:
            body = b'{"data":[],"rows":0}'
        return _FakeResp(body)

    since = datetime(2026, 10, 17, tzinfo=UTC)
    until = datetime(2026, 11, 16, tzinfo=UTC)
    points = fetch_algospecial_h1("EUR/USD", since, until, opener=opener)
    assert len(points) == 1
    assert points[0].close == 1.05
    assert len(calls) >= 2


def test_fetch_algospecial_h1_404_no_walkback() -> None:
    import trendalgo.market.algospecial_forex as mod

    mod._LAST_GOOD_UNTIL = None
    calls = 0

    def opener(req: object, timeout: float = 0) -> _FakeResp:  # noqa: ARG001
        nonlocal calls
        calls += 1
        raise urllib.error.HTTPError("https://x", 404, "Not Found", None, None)  # type: ignore[arg-type]

    since = datetime(2025, 10, 1, tzinfo=UTC)
    until = datetime(2025, 10, 31, tzinfo=UTC)
    with pytest.raises(AlgoSpecialUnsupportedError):
        fetch_algospecial_h1("USD/ARS", since, until, opener=opener)
    assert calls == 1


def test_fetch_algospecial_h1_429_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    import json

    import trendalgo.market.algospecial_forex as mod

    mod._LAST_GOOD_UNTIL = None
    monkeypatch.setattr(mod.time, "sleep", lambda _s: None)
    monkeypatch.setattr(mod, "_MIN_H1_BARS", 1)
    calls = 0
    rows = [
        {
            "Timestamp": "2025.10.01 00:00:00",
            "Open": 1,
            "High": 1.1,
            "Low": 0.9,
            "Close": 1.05,
            "TickVolume": 1,
        }
    ]
    payload = json.dumps({"data": rows}).encode()

    def opener(req: object, timeout: float = 0) -> _FakeResp:  # noqa: ARG001
        nonlocal calls
        calls += 1
        if calls == 1:
            raise urllib.error.HTTPError("https://x", 429, "Too Many", None, None)  # type: ignore[arg-type]
        return _FakeResp(payload)

    since = datetime(2025, 10, 1, tzinfo=UTC)
    until = datetime(2025, 10, 2, tzinfo=UTC)
    points = fetch_algospecial_h1("EUR/USD", since, until, opener=opener)
    assert len(points) == 1
    assert calls == 2


def test_fetch_algospecial_h1_paces_each_http() -> None:
    import trendalgo.market.algospecial_forex as mod

    mod._LAST_GOOD_UNTIL = None

    class _Gate:
        def __init__(self) -> None:
            self.n = 0

        def wait(self) -> None:
            self.n += 1

    gate = _Gate()
    calls = 0

    def opener(req: object, timeout: float = 0) -> _FakeResp:  # noqa: ARG001
        nonlocal calls
        calls += 1
        if calls == 1:
            return _FakeResp(b'{"data":[],"rows":0}')
        body = (
            b'{"data":[{"Timestamp":"2025.10.15 00:00:00","Open":1,"High":1.1,'
            b'"Low":0.9,"Close":1.05,"TickVolume":1}]}'
        )
        return _FakeResp(body)

    since = datetime(2026, 10, 17, tzinfo=UTC)
    until = datetime(2026, 11, 16, tzinfo=UTC)
    points = fetch_algospecial_h1("EUR/USD", since, until, opener=opener, pace=gate)
    assert len(points) == 1
    assert gate.n == calls >= 2
