"""Fixtures for the device app. Every test gets its own profile folder, never the real one."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

from trendalgo.device.context import DeviceContext, open_context
from trendalgo.device.jobs import CANDLE_SOURCE, synthetic_frame
from trendalgo.device.profile import CANDLES_ENV, DATA_ENV, PROFILE_ENV
from trendalgo.device.workers import WorkerPool
from trendalgo.market.ohlcv_cache import OhlcvCache
from trendalgo.market.symbols import base_symbol
from trendalgo.market.types import OhlcvPoint


@pytest.fixture(autouse=True)
def isolated_profile(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # Tests must never reach the owner's real data folder, even when the shell sets TRENDALGO_DATA_DIR.
    monkeypatch.setenv(PROFILE_ENV, str(tmp_path / "profile"))
    monkeypatch.delenv(CANDLES_ENV, raising=False)
    monkeypatch.delenv(DATA_ENV, raising=False)
    # The repo conftest sets the synthetic market for every test. Device scan tests inject their own market
    # and must take the live code path, so the synthetic switch is removed here.
    monkeypatch.delenv("TRENDALGO_MARKET_SOURCE", raising=False)


@pytest.fixture
def ctx(tmp_path: Path) -> DeviceContext:
    return open_context(tmp_path / "profile")


@pytest.fixture
def pool() -> Iterator[WorkerPool]:
    worker_pool = WorkerPool()
    yield worker_pool
    worker_pool.shutdown()


@pytest.fixture
def seed(ctx: DeviceContext) -> Callable[..., Path]:
    """Write synthetic kraken candles into the profile's candle file. Returns that file's path."""

    def _seed(*, pair: str = "BTC/USD", timeframe: str = "1h", bars: int = 300) -> Path:
        path = ctx.databases["candles"]
        frame = synthetic_frame(bars)
        points = [
            OhlcvPoint(
                time=1_700_000_000 + i * 3600,
                open=float(row.open),
                high=float(row.high),
                low=float(row.low),
                close=float(row.close),
                volume=float(row.volume),
            )
            for i, row in enumerate(frame.itertuples())
        ]
        OhlcvCache(path).upsert(CANDLE_SOURCE, base_symbol(pair), timeframe, points)
        return path

    return _seed
