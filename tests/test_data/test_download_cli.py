"""CLI and download helpers for trendalgo.data.download."""

from __future__ import annotations

from pathlib import Path

import pytest

from trendalgo.data import download


def test_download_ohlcv_mocked(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeExchange:
        def fetch_ohlcv(self, pair: str, timeframe: str, limit: int) -> list[list[float]]:
            del pair, timeframe, limit
            return [[1_700_000_000_000, 1, 2, 0.5, 1.5, 10]]

    monkeypatch.setattr(download, "_exchange", lambda _id="kraken": FakeExchange())
    rows = download.download_ohlcv(limit=1)
    assert len(rows) == 1


def test_main_success_and_failures(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeExchange:
        def fetch_ohlcv(self, *_args, **_kwargs) -> list[list[float]]:
            return [[1_700_000_000_000, 1, 2, 0.5, 1.5, 10]]

    monkeypatch.setattr(download, "_exchange", lambda _id="kraken": FakeExchange())
    code = download.main(["--out", str(tmp_path / "out"), "--limit", "1"])
    assert code == 0
    assert list((tmp_path / "out").glob("*.csv"))

    class BrokenExchange:
        def fetch_ohlcv(self, *_args, **_kwargs) -> list[list[float]]:
            raise RuntimeError("network")

    monkeypatch.setattr(download, "_exchange", lambda _id="kraken": BrokenExchange())
    assert download.main(["--limit", "1"]) == 1

    class EmptyExchange:
        def fetch_ohlcv(self, *_args, **_kwargs) -> list[list[float]]:
            return []

    monkeypatch.setattr(download, "_exchange", lambda _id="kraken": EmptyExchange())
    assert download.main(["--limit", "1"]) == 1
