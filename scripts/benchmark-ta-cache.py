#!/usr/bin/env python3
"""Benchmark TA cache stack — report p50/p95 ms per bot-detail TA path."""

from __future__ import annotations

import statistics
import time
from typing import Any

from trendalgo.ta.cache import ohlcv_list_to_df, get_ta_signal_cache, reset_all_ta_caches
from trendalgo.ta.signals import resolve_preset, signals_for_preset


def _ohlcv(n: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    price = 50_000.0
    for i in range(n):
        p = price + (i % 17) * 8
        rows.append(
            {
                "time": 1_700_000_000 + i,
                "open": p - 5,
                "high": p + 10,
                "low": p - 10,
                "close": p,
                "volume": 1.0,
            }
        )
    return rows


def _bot(strategy_id: str = "RSI", **params: Any) -> dict[str, Any]:
    return {
        "id": 1,
        "pair": "BTC/USD",
        "timeframe": "1S",
        "strategy_id": strategy_id,
        "equity_usd": 1000.0,
        "ta_params": params or {"timeperiod": 14},
    }


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = int(round((pct / 100) * (len(ordered) - 1)))
    return ordered[max(0, min(idx, len(ordered) - 1))]


def _baseline_ms(ohlcv: list[dict], bot: dict[str, Any], runs: int) -> list[float]:
    df = ohlcv_list_to_df(ohlcv)
    preset = resolve_preset(str(bot["strategy_id"]), dict(bot.get("ta_params") or {}))
    times: list[float] = []
    for _ in range(runs):
        t0 = time.perf_counter()
        signals_for_preset(df, preset)
        times.append((time.perf_counter() - t0) * 1000)
    return times


def _cached_exact_ms(ohlcv: list[dict], bot: dict[str, Any], runs: int) -> list[float]:
    df = ohlcv_list_to_df(ohlcv, pair="BTC/USD", fetch_tf="1s")
    cache = get_ta_signal_cache()
    cache.get_or_compute_signals(df, ohlcv, bot)
    times: list[float] = []
    for _ in range(runs):
        t0 = time.perf_counter()
        cache.get_or_compute_signals(df, ohlcv, bot)
        times.append((time.perf_counter() - t0) * 1000)
    return times


def main() -> None:
    bars = 3600
    runs = 20
    ohlcv = _ohlcv(bars)

    reset_all_ta_caches()
    base_times = _baseline_ms(ohlcv, _bot(), runs)
    reset_all_ta_caches()
    identical = _bot()
    cache_times = _cached_exact_ms(ohlcv, identical, runs)

    base_p95 = _percentile(base_times, 95)
    cache_p95 = _percentile(cache_times, 95)
    savings = 0.0 if base_p95 <= 0 else (1 - cache_p95 / base_p95) * 100

    print(f"bars={bars} runs={runs}")
    print(f"baseline p50={statistics.median(base_times):.2f}ms p95={base_p95:.2f}ms")
    print(f"cached(exact hit) p50={statistics.median(cache_times):.2f}ms p95={cache_p95:.2f}ms")
    print(f"p95_savings_pct={savings:.1f}")
    print(f"bump_sub_minute_cap={'yes' if savings >= 40 else 'no'} (threshold 40%, 1S stays 1)")


if __name__ == "__main__":
    main()
