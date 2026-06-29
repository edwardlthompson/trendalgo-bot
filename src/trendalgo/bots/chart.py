"""Bot price chart payload — OHLCV from SQLite + close line for legacy chart widgets."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast

from trendalgo.bots.limits import chart_lookback_seconds
from trendalgo.constants.timeframes import timeframe_for_fetch
from trendalgo.market.service import PriceHistoryService


def bot_chart_payload(bot: dict[str, Any], data_dir: Path) -> dict[str, Any]:
    raw_tf = str(bot.get("timeframe") or "60")
    fetch_tf = timeframe_for_fetch(raw_tf)
    until = datetime.now(UTC)
    lookback = timedelta(seconds=chart_lookback_seconds(raw_tf))
    since = until - lookback
    service = PriceHistoryService(data_dir / "prices.db")
    candles_raw = service.get_ohlcv(str(bot["pair"]), fetch_tf, since, until)
    ohlcv = [
        {
            "time": int(p.time),
            "open": float(p.open),
            "high": float(p.high),
            "low": float(p.low),
            "close": float(p.close),
            "volume": float(p.volume),
        }
        for p in candles_raw
    ]
    chart = [{"time": c["time"], "value": c["close"]} for c in ohlcv]
    return {"chart": chart, "ohlcv": ohlcv}


def bot_close_chart(bot: dict[str, Any], data_dir: Path) -> list[dict[str, int | float]]:
    payload = bot_chart_payload(bot, data_dir)
    return cast(list[dict[str, int | float]], payload["chart"])
