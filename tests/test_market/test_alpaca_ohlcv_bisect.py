"""Alpaca multi-bars bisect recovery when one symbol triggers HTTP 400."""

from __future__ import annotations

import io
import json
import urllib.error
from datetime import UTC, datetime

from trendalgo.market.alpaca_ohlcv import fetch_alpaca_equity_bars_multi


class _FakeResp:
    def __init__(self, body: dict) -> None:
        self._buf = json.dumps(body).encode("utf-8")

    def read(self) -> bytes:
        return self._buf

    def __enter__(self) -> _FakeResp:
        return self

    def __exit__(self, *args: object) -> None:
        return None


def test_multi_bars_bisects_http_400_bad_symbol() -> None:
    calls: list[list[str]] = []

    def _fake_open(req: object, timeout: int = 15) -> _FakeResp:
        del timeout
        url = str(getattr(req, "full_url", ""))
        from urllib.parse import parse_qs, urlparse

        syms = parse_qs(urlparse(url).query)["symbols"][0].split(",")
        calls.append(syms)
        if "BADSYM" in syms:
            raise urllib.error.HTTPError(url, 400, "Bad Request", None, io.BytesIO(b"bad"))  # type: ignore[arg-type]
        bars = {
            s: [{"t": "2026-11-01T15:00:00Z", "o": 10.0, "h": 11.0, "l": 9.0, "c": 10.5, "v": 100}]
            for s in syms
        }
        return _FakeResp({"bars": bars})

    symbols = [f"SYM{i}" for i in range(9)] + ["BADSYM"]
    since = datetime(2026, 11, 1, tzinfo=UTC)
    until = datetime(2026, 11, 2, tzinfo=UTC)
    out = fetch_alpaca_equity_bars_multi(
        symbols,
        "1d",
        since,
        until,
        credentials=("key", "sec"),
        opener=_fake_open,
        chunk_size=10,
        max_calls_per_min=10_000,
    )
    assert len(out) == 9
    assert "BADSYM" not in out
    assert all(f"SYM{i}" in out for i in range(9))
    assert len(calls) > 1
