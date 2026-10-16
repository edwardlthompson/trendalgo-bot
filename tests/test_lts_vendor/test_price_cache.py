"""SQLite-backed OHLCV price cache shared by LTS backtest workers."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

import pytest

from trendalgo.lts_vendor import install_import_shims
from trendalgo.lts_vendor.shims import api_coingecko as cg
from trendalgo.lts_vendor.shims import database_cache
from trendalgo.lts_vendor.shims.database_cache import PriceCache

HOUR = 3600.0
T0 = 1_790_000_000.0


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> dict[str, float]:
    now = {"t": T0}
    monkeypatch.setattr(database_cache, "_now", lambda: now["t"])
    return now


def _candles(last_open: float, count: int = 48) -> list[dict[str, Any]]:
    return [
        {
            "ts": last_open - (count - 1 - i) * HOUR,
            "open": 0.1 + i,
            "high": 0.2 + i,
            "low": 0.05 + i,
            "close": 0.1 + 0.2 + i,  # 0.30000000000000004 must survive the disk round trip
            "volume": 3.0 + i,
        }
        for i in range(count)
    ]


def _stored_series_count(db: Path) -> int:
    with closing(sqlite3.connect(db)) as conn:
        return int(conn.execute("SELECT COUNT(*) FROM ohlcv_series").fetchone()[0])


def test_memory_only_cache_round_trips_and_tags_source(clock: dict[str, float]) -> None:
    cache = PriceCache()
    assert cache.db_path is None
    assert cache.cache_ohlcv_rows("Kraken", "btc", "1H", _candles(T0), source="kraken_ohlcv") == 48
    found, rows = cache.get_ohlcv_rows("kraken", "BTC", "1h", max_age_hours=12)
    assert found is True
    assert rows is not None and len(rows) == 48
    assert rows[-1]["source"] == "kraken_ohlcv"


def test_series_persist_across_instances_with_exact_floats(
    tmp_path: Path, clock: dict[str, float]
) -> None:
    db = tmp_path / "lts_price_cache.db"
    candles = _candles(T0)
    PriceCache(db).cache_ohlcv_rows("kraken", "BTC", "1h", candles, source="kraken_ohlcv")

    found, rows = PriceCache(db).get_ohlcv_rows("kraken", "BTC", "1h", max_age_hours=12)
    assert found is True
    assert rows is not None
    assert [r["close"] for r in rows] == [c["close"] for c in candles]
    assert [r["ts"] for r in rows] == [c["ts"] for c in candles]
    assert rows[0]["source"] == "kraken_ohlcv"


def test_entries_expire_after_max_age_across_restarts(
    tmp_path: Path, clock: dict[str, float]
) -> None:
    db = tmp_path / "lts_price_cache.db"
    PriceCache(db).cache_ohlcv_rows("polygon", "BTC", "1d", _candles(T0), source="polygon_api")

    clock["t"] = T0 + 11 * HOUR
    assert PriceCache(db).get_ohlcv_rows("polygon", "BTC", "1d", max_age_hours=12)[0] is True

    clock["t"] = T0 + 13 * HOUR
    assert PriceCache(db).get_ohlcv_rows("polygon", "BTC", "1d", max_age_hours=12) == (False, None)


def test_hourly_series_must_reach_the_present(tmp_path: Path, clock: dict[str, float]) -> None:
    db = tmp_path / "lts_price_cache.db"
    PriceCache(db).cache_ohlcv_rows("kraken", "BTC", "1h", _candles(T0), source="kraken_ohlcv")

    clock["t"] = T0 + 2 * HOUR  # newest candle opened 2 h ago: still usable
    assert PriceCache(db).get_ohlcv_rows("kraken", "BTC", "1h", max_age_hours=12)[0] is True

    clock["t"] = T0 + 4 * HOUR  # newest candle opened 4 h ago: truncated download, refetch
    assert PriceCache(db).get_ohlcv_rows("kraken", "BTC", "1h", max_age_hours=12) == (False, None)


def test_clock_moving_backwards_forces_refetch(clock: dict[str, float]) -> None:
    cache = PriceCache()
    cache.cache_ohlcv_rows("kraken", "BTC", "1d", _candles(T0), source="kraken_ohlcv")
    clock["t"] = T0 - HOUR
    assert cache.get_ohlcv_rows("kraken", "BTC", "1d", max_age_hours=12) == (False, None)


def test_synthetic_rows_are_never_written_to_disk(tmp_path: Path, clock: dict[str, float]) -> None:
    db = tmp_path / "lts_price_cache.db"
    fake = [dict(candle, synthetic=True) for candle in _candles(T0)]
    writer = PriceCache(db)
    writer.cache_ohlcv_rows("kraken", "BTC", "1h", fake, source="synthetic")

    assert writer.get_ohlcv_rows("kraken", "BTC", "1h", max_age_hours=12)[0] is True
    assert PriceCache(db).get_ohlcv_rows("kraken", "BTC", "1h", max_age_hours=12) == (False, None)
    assert _stored_series_count(db) == 0


def test_database_directory_is_created_and_uses_wal(
    tmp_path: Path, clock: dict[str, float]
) -> None:
    db = tmp_path / "nested" / "data" / "lts_price_cache.db"
    PriceCache(db).cache_ohlcv_rows("kraken", "BTC", "1h", _candles(T0), source="kraken_ohlcv")

    assert db.exists()
    with closing(sqlite3.connect(db)) as conn:
        assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    assert PriceCache(db).get_ohlcv_rows("kraken", "BTC", "1h", max_age_hours=12)[0] is True


def test_unusable_database_falls_back_to_memory(tmp_path: Path, clock: dict[str, float]) -> None:
    db = tmp_path / "lts_price_cache.db"
    db.write_bytes(b"this is not a sqlite database" * 64)

    cache = PriceCache(db)
    assert cache.db_path is None
    cache.cache_ohlcv_rows("kraken", "BTC", "1h", _candles(T0), source="kraken_ohlcv")
    assert cache.get_ohlcv_rows("kraken", "BTC", "1h", max_age_hours=12)[0] is True


def _load_btc_1h(db: Path) -> Any:
    """Load BTC 1h with Kraken, Polygon and CMC all empty (only synthetic can answer)."""
    install_import_shims()
    from trendalgo.lts_vendor.backtesting.data_loader import BacktestDataLoader
    from trendalgo.lts_vendor.backtesting.params import BacktestLoaderParams

    lp = BacktestLoaderParams(
        coingecko_calls_per_minute=30,
        cmc_api_key="",
        cmc_calls_per_minute=30,
        polygon_calls_per_minute=5,
        ohlcv_min_1h_bars_per_day=20,
        ohlcv_min_1h_bars_slack=2,
        ohlcv_min_1h_bars_floor=48,
        ohlcv_min_1d_bars_slack=2,
        ohlcv_min_1d_bars_floor=14,
    )
    return BacktestDataLoader(cache=PriceCache(db), loader_params=lp).load(
        "BTC", timeframe="1h", days=30, gecko_id="bitcoin"
    )


def test_loader_labels_synthetic_candles_and_skips_the_disk_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("TRENDALGO_MARKET_SOURCE", raising=False)
    monkeypatch.setenv("BACKTEST_ALLOW_SYNTHETIC", "1")
    monkeypatch.setattr(cg, "fetch_kraken_hourly_rows", lambda *_a, **_k: None)
    db = tmp_path / "lts_price_cache.db"

    loaded = _load_btc_1h(db)

    assert loaded.frame is not None
    assert loaded.source == "synthetic"
    assert _stored_series_count(db) == 0


def test_loader_skips_coin_without_candles_when_synthetic_is_off(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("TRENDALGO_MARKET_SOURCE", raising=False)
    monkeypatch.delenv("BACKTEST_ALLOW_SYNTHETIC", raising=False)
    monkeypatch.setattr(cg, "fetch_kraken_hourly_rows", lambda *_a, **_k: None)
    db = tmp_path / "lts_price_cache.db"

    loaded = _load_btc_1h(db)

    assert loaded.frame is None
    assert loaded.source == "none"
    assert loaded.skip_reason == "no_intraday_ohlcv"
    assert _stored_series_count(db) == 0
