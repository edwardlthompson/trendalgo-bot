"""Data path: TRENDALGO_DATA_DIR points the device at the API's files, which it reads and never changes."""

from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

import pytest

from trendalgo.bots.orchestrator import BotOrchestrator
from trendalgo.device.app import prepare_databases
from trendalgo.device.context import open_context
from trendalgo.device.jobs import MIN_BARS, NoCandlesError, load_candles
from trendalgo.device.profile import CANDLES_ENV, DATA_ENV, db_paths
from trendalgo.device.stores import read_bots, read_snapshot, read_trades
from trendalgo.market.ohlcv_cache import OhlcvCache
from trendalgo.market.types import OhlcvPoint
from trendalgo.risk.journal import TradeJournal
from trendalgo.scanner.store import ScannerStore


def _points(count: int) -> list[OhlcvPoint]:
    return [
        OhlcvPoint(
            time=1_700_000_000 + i * 3600,
            open=100.0 + i,
            high=101.0 + i,
            low=99.0 + i,
            close=100.5 + i,
            volume=10.0,
        )
        for i in range(count)
    ]


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_db_paths_default_to_the_profile_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(DATA_ENV, raising=False)
    paths = db_paths(tmp_path)
    assert all(path.parent == tmp_path for path in paths.values())


def test_data_dir_points_the_four_databases_at_the_api_folder(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data = tmp_path / "data"
    monkeypatch.setenv(DATA_ENV, str(data))
    paths = db_paths(tmp_path / "profile")
    assert paths["scanner"] == data / "scanner.db"
    assert paths["bots"] == data / "bots.db"
    assert paths["journal"] == data / "journal.db"
    assert paths["candles"] == data / "ohlcv_prices.db"


def test_candle_env_still_wins_for_the_candle_file_alone(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(DATA_ENV, str(tmp_path / "data"))
    monkeypatch.setenv(CANDLES_ENV, str(tmp_path / "elsewhere.db"))
    paths = db_paths(tmp_path / "profile")
    assert paths["candles"] == tmp_path / "elsewhere.db"
    assert paths["scanner"] == tmp_path / "data" / "scanner.db"


def test_open_context_marks_files_outside_the_profile_as_shared(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(DATA_ENV, raising=False)
    assert open_context(tmp_path / "own").shared == frozenset()
    monkeypatch.setenv(DATA_ENV, str(tmp_path / "data"))
    ctx = open_context(tmp_path / "profile")
    assert ctx.shared == frozenset({"scanner", "bots", "journal", "candles"})


def test_prepare_databases_leaves_shared_files_alone(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data = tmp_path / "data"
    data.mkdir()
    monkeypatch.setenv(DATA_ENV, str(data))
    sqlite3.connect(data / "scanner.db").close()
    ctx = open_context(tmp_path / "profile")
    assert prepare_databases(ctx) == []
    with sqlite3.connect(data / "scanner.db") as conn:
        assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "delete"


def test_device_readers_do_not_change_the_api_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data = tmp_path / "data"
    data.mkdir()
    monkeypatch.setenv(DATA_ENV, str(data))
    BotOrchestrator(data / "bots.db")
    TradeJournal(data / "journal.db")
    ScannerStore(data / "scanner.db")
    OhlcvCache(data / "ohlcv_prices.db").upsert("kraken", "BTC", "1h", _points(MIN_BARS + 5))
    files = [data / name for name in ("bots.db", "journal.db", "scanner.db", "ohlcv_prices.db")]
    before = {path.name: _digest(path) for path in files}

    paths = db_paths(tmp_path / "profile")
    assert read_snapshot(paths["scanner"]) is None
    assert read_bots(paths["bots"]) == []
    assert read_trades(paths["journal"]) == []
    load_candles(paths["candles"], pair="BTC/USD", timeframe="1h")

    assert {path.name: _digest(path) for path in files} == before


def test_load_candles_reads_the_base_symbol_the_api_stores(tmp_path: Path) -> None:
    path = tmp_path / "ohlcv_prices.db"
    OhlcvCache(path).upsert("kraken", "BTC", "1h", _points(MIN_BARS + 5))
    assert len(load_candles(path, pair="BTC/USD", timeframe="1h")) == MIN_BARS + 5
    assert len(load_candles(path, pair="btc/usd", timeframe="1h")) == MIN_BARS + 5


def test_load_candles_names_the_pair_when_it_has_no_bars(tmp_path: Path) -> None:
    path = tmp_path / "ohlcv_prices.db"
    OhlcvCache(path).upsert("kraken", "BTC", "1h", _points(MIN_BARS + 5))
    with pytest.raises(NoCandlesError, match="0 bars for ETH/USD 1h"):
        load_candles(path, pair="ETH/USD", timeframe="1h")
