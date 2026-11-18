"""Covering FX OHLC cache helper for All-TA / Market Context."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from trendalgo.device.scan_base_ohlcv_forex_fallback import (
    load_covering_cached_ohlcv,
    normalize_fx_cache_pair,
)
from trendalgo.market.ohlcv_disk_cache import save_cached_ohlcv
from trendalgo.market.types import OhlcvPoint


def test_normalize_fx_cache_pair_from_compact_symbol() -> None:
    assert normalize_fx_cache_pair("EURUSD", "") == "EUR/USD"
    assert normalize_fx_cache_pair("EUR", "EUR/GBP") == "EUR/GBP"


def test_load_covering_cached_ohlcv_finds_wide_bucket(tmp_path: Path) -> None:
    end = datetime(2026, 11, 15, tzinfo=UTC)
    points = [
        OhlcvPoint(
            time=int((end - timedelta(hours=i)).timestamp()),
            open=1.0,
            high=1.1,
            low=0.9,
            close=1.05,
            volume=2.0,
        )
        for i in range(200)
    ]
    points.sort(key=lambda p: p.time)
    save_cached_ohlcv(
        tmp_path,
        "EUR/USD",
        "1h",
        datetime(2026, 10, 1, tzinfo=UTC),
        datetime(2026, 11, 16, tzinfo=UTC),
        points,
    )
    got = load_covering_cached_ohlcv(
        tmp_path,
        "EUR/USD",
        "1h",
        datetime(2026, 10, 19, tzinfo=UTC),
        datetime(2026, 11, 18, tzinfo=UTC),
        min_bars=50,
    )
    assert got is not None
    assert len(got) >= 50
