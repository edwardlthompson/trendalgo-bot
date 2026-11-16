"""TradFi universe: seed length + live cache fallback."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from trendalgo.brokers.tradfi_universe import (
    clear_tradfi_universe_cache,
    is_tradfi_symbol,
    load_seed_universe,
    load_tradfi_universe,
)
from trendalgo.market.ohlcv_disk_cache import load_cached_ohlcv, save_cached_ohlcv
from trendalgo.market.types import OhlcvPoint


def test_seed_universe_length_500() -> None:
    clear_tradfi_universe_cache()
    uni = load_tradfi_universe()
    assert len(uni) == 500
    assert uni == load_seed_universe()
    assert "AAPL" in uni
    assert is_tradfi_symbol("aapl/usd")


def test_unknown_symbol_rejected() -> None:
    assert not is_tradfi_symbol("NOTAREALTICKERXYZ")


def test_live_cache_preferred_over_seed(tmp_path: Path) -> None:
    from trendalgo.device.profile import write_json

    day = datetime.now(tz=UTC).strftime("%Y-%m-%d")
    write_json(
        tmp_path / "tradfi_universe_live.json",
        {"version": 1, "day": day, "count": 3, "symbols": ["AAA", "BBB", "CCC"]},
    )
    with patch(
        "trendalgo.brokers.tradfi_universe._fetch_and_cache_live",
        return_value=None,
    ):
        # Fresh cache should not call fetch.
        uni = load_tradfi_universe(root=tmp_path)
    assert uni == ("AAA", "BBB", "CCC")


def test_live_fetch_failure_falls_back_to_seed(tmp_path: Path) -> None:
    with patch(
        "trendalgo.brokers.tradfi_universe._fetch_and_cache_live",
        return_value=None,
    ):
        uni = load_tradfi_universe(root=tmp_path)
    assert len(uni) == 500
    assert "AAPL" in uni


def test_disk_cache_hit(tmp_path: Path) -> None:
    until = datetime.now(UTC)
    since = until - timedelta(days=2)
    points = [
        OhlcvPoint(time=int(since.timestamp()), open=1, high=2, low=0.5, close=1.5, volume=10)
    ]
    save_cached_ohlcv(tmp_path, "AAPL", "1d", since, until, points)
    loaded = load_cached_ohlcv(tmp_path, "AAPL", "1d", since, until)
    assert loaded is not None
    assert loaded[0].close == 1.5
