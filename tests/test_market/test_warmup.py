"""Bot-scoped OHLCV warmup."""

from __future__ import annotations

import os
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from trendalgo.market.service import PriceHistoryService
from trendalgo.market.types import OhlcvPoint
from trendalgo.market.warmup import collect_bot_series, get_warmup_runner


def test_collect_bot_series_dedupes_pair_timeframe() -> None:
    bots = [
        {"id": 1, "label": "A", "pair": "BTC/USD", "timeframe": "60"},
        {"id": 2, "label": "B", "pair": "BTC/USD", "timeframe": "60"},
        {"id": 3, "label": "C", "pair": "ETH/USD", "timeframe": "5"},
    ]
    series = collect_bot_series(bots)
    assert len(series) == 2
    btc = next(s for s in series if s.pair == "BTC/USD")
    assert len(btc.bot_labels) == 2


def test_warmup_uses_synthetic_without_network() -> None:
    data_dir = Path(tempfile.mkdtemp(prefix="trendalgo-warmup-"))
    os.environ["TRENDALGO_DATA_DIR"] = str(data_dir)
    os.environ["TRENDALGO_MARKET_SOURCE"] = "synthetic"
    bots = [{"id": 1, "label": "Bot-1", "pair": "BTC/USD", "timeframe": "60"}]
    runner = get_warmup_runner(data_dir)
    job = runner.start(bots)
    assert job["status"] == "running"
    if runner._thread:
        runner._thread.join(timeout=10)
    snap = runner.snapshot()
    assert snap is not None
    assert snap["status"] == "complete"
    assert snap["completed_series"] == 1
    assert snap["bars_cached"] > 0


def test_incremental_cache_avoids_full_refetch() -> None:
    data_dir = Path(tempfile.mkdtemp(prefix="trendalgo-incr-"))
    service = PriceHistoryService(data_dir / "prices.db")
    since = datetime.now(UTC) - timedelta(hours=3)
    until = datetime.now(UTC)
    from trendalgo.market.symbols import base_symbol

    sym = base_symbol("BTC/USD").upper()
    step = 3600
    since_ts = int(since.timestamp())
    points = [
        OhlcvPoint(time=since_ts + i * step, open=1, high=1, low=1, close=1, volume=1)
        for i in range(4)
    ]
    service._ohlcv.upsert("kraken", sym, "1h", points)

    with (
        patch("trendalgo.market.service._use_synthetic", return_value=False),
        patch("trendalgo.market.service.fetch_kraken_ohlcv") as mock_fetch,
    ):
        mock_fetch.return_value = []
        out = service.get_ohlcv("BTC/USD", "1h", since, until)
        assert len(out) >= 3
        mock_fetch.assert_not_called()
