"""Cache path must match direct signals_for_preset for core strategies (R12)."""

from __future__ import annotations

import numpy as np
import pytest

from trendalgo.ta.cache import TaSignalCache, ohlcv_list_to_df, reset_all_ta_caches
from trendalgo.ta.signals import resolve_preset, signals_for_preset

PARITY_CASES: list[tuple[str, dict]] = [
    ("RSI", {"timeperiod": 14}),
    ("SMA", {"fast": 10, "slow": 30}),
    ("MACD", {"fastperiod": 12, "slowperiod": 26, "signalperiod": 9}),
    ("EMA", {"timeperiod": 20}),
    ("ROC", {"timeperiod": 10}),
    ("MOM", {"timeperiod": 10}),
]


def _ohlcv(n: int, *, start_ts: int = 1_700_000_000, step: int = 3600) -> list[dict]:
    rows: list[dict] = []
    price = 50_000.0
    for i in range(n):
        wave = (i % 7) * 120
        p = price + wave
        rows.append(
            {
                "time": start_ts + i * step,
                "open": p - 10,
                "high": p + 20,
                "low": p - 20,
                "close": p,
                "volume": 1.0,
            }
        )
    return rows


def _bot(strategy_id: str, ta_params: dict) -> dict:
    return {
        "id": 1,
        "pair": "BTC/USD",
        "timeframe": "60",
        "strategy_id": strategy_id,
        "equity_usd": 1000.0,
        "ta_params": ta_params,
    }


@pytest.fixture(autouse=True)
def _clean() -> None:
    reset_all_ta_caches()
    yield
    reset_all_ta_caches()


@pytest.mark.parametrize(("strategy_id", "ta_params"), PARITY_CASES)
def test_cache_miss_matches_direct(strategy_id: str, ta_params: dict) -> None:
    ohlcv = _ohlcv(120)
    df = ohlcv_list_to_df(ohlcv)
    bot = _bot(strategy_id, ta_params)
    preset = resolve_preset(strategy_id, ta_params)
    direct_e, direct_x = signals_for_preset(df, preset)

    cache = TaSignalCache()
    cache_e, cache_x, meta = cache.get_or_compute_signals(df, ohlcv, bot)
    assert meta.hit == "miss"
    np.testing.assert_array_equal(cache_e, direct_e)
    np.testing.assert_array_equal(cache_x, direct_x)
