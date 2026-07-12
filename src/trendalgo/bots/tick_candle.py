"""Latest-candle loading for scheduled bot ticks."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from trendalgo.bots.limits import interval_seconds
from trendalgo.constants.timeframes import timeframe_for_fetch
from trendalgo.market.service import PriceHistoryService
from trendalgo.strategies.runtime.contract import Candle


class BotCandleLoader:
    def __init__(self, data_dir: Path) -> None:
        self._market = PriceHistoryService(data_dir / "prices.db")

    def __call__(self, bot: dict[str, Any]) -> Candle:
        timeframe = str(bot.get("timeframe") or "60")
        until = datetime.now(UTC)
        since = until - timedelta(seconds=max(120, interval_seconds(timeframe) * 2))
        bars = self._market.get_ohlcv(
            str(bot["pair"]),
            timeframe_for_fetch(timeframe),
            since,
            until,
            exchange_id=str(bot["exchange"]),
        )
        if not bars:
            raise RuntimeError("no OHLCV candle available")
        bar = bars[-1]
        return Candle(
            timestamp_ms=bar.time * 1000,
            open=bar.open,
            high=bar.high,
            low=bar.low,
            close=bar.close,
            volume=bar.volume,
        )
