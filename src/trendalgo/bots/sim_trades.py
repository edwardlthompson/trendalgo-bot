"""Simulated backtest trades mapped onto price chart (max 30D)."""

from __future__ import annotations

from typing import Any

from trendalgo.constants.timeframes import timeframe_for_fetch
from trendalgo.ta.cache import CacheMeta, get_ta_signal_cache, ohlcv_list_to_df
from trendalgo.ta.sweep import trades_from_signals


def simulated_trades_for_bot(
    bot: dict[str, Any],
    ohlcv: list[dict[str, Any]],
    *,
    chart: list[dict[str, int | float]] | None = None,
    return_meta: bool = False,
) -> list[dict[str, Any]] | tuple[list[dict[str, Any]], CacheMeta]:
    if len(ohlcv) < 10:
        empty: list[dict[str, Any]] = []
        if return_meta:
            return empty, CacheMeta(hit="miss", shared=False, warmup_bars=0, compute_ms=0.0)
        return empty
    chart_line = chart or [{"time": c["time"], "value": c["close"]} for c in ohlcv]
    tf = str(bot.get("timeframe") or "60")
    fetch_tf = timeframe_for_fetch(tf)
    df = ohlcv_list_to_df(ohlcv, pair=str(bot["pair"]), fetch_tf=fetch_tf)
    cache = get_ta_signal_cache()
    try:
        entries, exits, meta = cache.get_or_compute_signals(df, ohlcv, bot)
    except (KeyError, ValueError, TypeError):
        empty = []
        if return_meta:
            return empty, CacheMeta(hit="miss", shared=False, warmup_bars=0, compute_ms=0.0)
        return empty
    stake = float(bot.get("equity_usd", 100))
    closes = df["close"].to_numpy(dtype=float)
    trades = trades_from_signals(
        pair=str(bot["pair"]),
        chart=chart_line,
        closes=closes,
        entries=entries,
        exits=exits,
        stake=stake,
    )
    if return_meta:
        return trades, meta
    return trades
