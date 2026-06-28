"""Tests for TA signal cache — exact hit, incremental tail, sharing, concurrency."""

from __future__ import annotations

import threading
from unittest.mock import patch

import numpy as np
import pytest

from trendalgo.ta.cache import (
    TaFingerprint,
    TaSignalCache,
    get_ta_signal_cache,
    ohlcv_list_to_df,
    preset_warmup_bars,
    reset_all_ta_caches,
    trim_df_for_bot,
)
from trendalgo.ta.signals import resolve_preset, signals_for_preset
from trendalgo.ta.signatures import OhlcvSignature, canonical_ta_params_hash


def _bot(**overrides: object) -> dict:
    base = {
        "id": 1,
        "pair": "BTC/USD",
        "timeframe": "60",
        "strategy_id": "RSI",
        "equity_usd": 1000.0,
        "ta_params": {"timeperiod": 14},
    }
    base.update(overrides)
    return base


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


@pytest.fixture(autouse=True)
def _clean_cache() -> None:
    reset_all_ta_caches()
    yield
    reset_all_ta_caches()


def test_canonical_ta_params_hash_normalizes_float_int() -> None:
    assert canonical_ta_params_hash({"timeperiod": 14}) == canonical_ta_params_hash(
        {"timeperiod": 14.0}
    )


def test_exact_hit_skips_recompute() -> None:
    cache = TaSignalCache()
    bot = _bot()
    ohlcv = _ohlcv(80)
    df = ohlcv_list_to_df(ohlcv)
    with patch("trendalgo.ta.cache.signals_for_preset", wraps=signals_for_preset) as mocked:
        cache.get_or_compute_signals(df, ohlcv, bot)
        assert mocked.call_count == 1
        _e, _x, meta = cache.get_or_compute_signals(df, ohlcv, bot)
        assert mocked.call_count == 1
        assert meta.hit == "exact"
        assert cache.stats.hits_exact == 1


def test_identical_bots_share_fingerprint() -> None:
    cache = TaSignalCache()
    bot_a = _bot(id=1, equity_usd=1000)
    bot_b = _bot(id=2, equity_usd=500)
    ohlcv = _ohlcv(80)
    df = ohlcv_list_to_df(ohlcv)
    with patch("trendalgo.ta.cache.signals_for_preset", wraps=signals_for_preset) as mocked:
        cache.get_or_compute_signals(df, ohlcv, bot_a)
        cache.get_or_compute_signals(df, ohlcv, bot_b)
        assert mocked.call_count == 1
        assert cache.stats.dedupe_savings == 1


@pytest.mark.parametrize(
    ("strategy_id", "ta_params"),
    [
        ("RSI", {"timeperiod": 14}),
        ("SMA", {"fast": 10, "slow": 30}),
        ("MACD", {"fastperiod": 12, "slowperiod": 26, "signalperiod": 9}),
    ],
)
def test_incremental_tail_matches_full(strategy_id: str, ta_params: dict) -> None:
    cache = TaSignalCache()
    bot = _bot(strategy_id=strategy_id, ta_params=ta_params)
    base = _ohlcv(120)
    extended = base + [_ohlcv(1, start_ts=base[-1]["time"] + 3600)[0]]
    df_ext = ohlcv_list_to_df(extended)
    preset = resolve_preset(strategy_id, ta_params)
    full_entries, full_exits = signals_for_preset(df_ext, preset)

    cache.get_or_compute_signals(ohlcv_list_to_df(base), base, bot)
    inc_entries, inc_exits, meta = cache.get_or_compute_signals(df_ext, extended, bot)
    assert meta.hit == "incremental"
    np.testing.assert_array_equal(inc_entries, full_entries)
    np.testing.assert_array_equal(inc_exits, full_exits)


def test_incremental_rejected_on_first_ts_change() -> None:
    cache = TaSignalCache()
    bot = _bot()
    base = _ohlcv(80)
    df_base = ohlcv_list_to_df(base)
    cache.get_or_compute_signals(df_base, base, bot)

    shifted = _ohlcv(81, start_ts=base[0]["time"] + 60)
    df_shift = ohlcv_list_to_df(shifted)
    with patch("trendalgo.ta.cache.signals_for_preset", wraps=signals_for_preset) as mocked:
        _e, _x, meta = cache.get_or_compute_signals(df_shift, shifted, bot)
        assert meta.hit == "miss"
        assert mocked.call_count == 1
        assert cache.stats.incremental_rejected == 0
        assert cache.stats.misses_full == 2


def test_config_invalidation() -> None:
    cache = TaSignalCache()
    old = _bot(strategy_id="RSI")
    new = _bot(strategy_id="MACD")
    cache.invalidate_for_bot_config_change(old, new)
    assert cache.stats.invalidations_config == 1


def test_lru_eviction() -> None:
    cache = TaSignalCache(max_entries=2)
    ohlcv = _ohlcv(60)
    df = ohlcv_list_to_df(ohlcv)
    for i in range(3):
        bot = _bot(strategy_id="RSI", ta_params={"timeperiod": 10 + i})
        cache.get_or_compute_signals(df, ohlcv, bot)
    assert cache.stats.evictions >= 1
    assert len(cache._entries) <= 2


def test_concurrent_same_fingerprint_single_compute() -> None:
    cache = TaSignalCache()
    bot = _bot()
    ohlcv = _ohlcv(80)
    df = ohlcv_list_to_df(ohlcv)
    barrier = threading.Barrier(10)
    errors: list[Exception] = []

    def worker() -> None:
        try:
            barrier.wait(timeout=5)
            cache.get_or_compute_signals(df, ohlcv, bot)
        except Exception as exc:
            errors.append(exc)

    with patch("trendalgo.ta.cache.signals_for_preset", wraps=signals_for_preset) as mocked:
        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)
        assert not errors
        assert mocked.call_count == 1


def test_preset_warmup_bars_ma_cross() -> None:
    preset = resolve_preset("SMA", {"fast": 10, "slow": 30})
    assert preset_warmup_bars(preset) >= 40


def test_ohlcv_signature_from_list() -> None:
    ohlcv = _ohlcv(5)
    sig = OhlcvSignature.from_ohlcv(ohlcv)
    assert sig.bar_count == 5
    assert sig.first_ts == ohlcv[0]["time"]
    assert sig.last_ts == ohlcv[-1]["time"]


def test_fingerprint_from_bot() -> None:
    fp = TaFingerprint.from_bot(_bot(timeframe="1S"))
    assert fp.timeframe == "1S"
    assert fp.pair == "BTC/USD"


def test_frame_cache_hit_skips_rebuild() -> None:
    ohlcv = _ohlcv(40)
    df1 = ohlcv_list_to_df(ohlcv, pair="BTC/USD", fetch_tf="60")
    df2 = ohlcv_list_to_df(ohlcv, pair="BTC/USD", fetch_tf="60")
    from trendalgo.ta.frame_cache import get_frame_cache

    stats = get_frame_cache().stats_payload()
    assert stats["hits"] >= 1
    assert df1 is df2


def test_ma_cross_indicator_cache_single_slow_compute() -> None:
    from trendalgo.ta.engine import _compute_uncached

    df = ohlcv_list_to_df(_ohlcv(80))
    preset = resolve_preset("SMA", {"fast": 10, "slow": 30})
    with patch("trendalgo.ta.engine._compute_uncached", wraps=_compute_uncached) as mocked:
        signals_for_preset(df, preset)
        assert mocked.call_count == 2
        signals_for_preset(df, preset)
        assert mocked.call_count == 2


def test_prewarm_populates_signal_cache(tmp_path) -> None:
    from unittest.mock import patch

    from trendalgo.ta.cache import get_ta_signal_cache
    from trendalgo.ta.prewarm import _prewarm_one

    bot = _bot()
    ohlcv = _ohlcv(40)

    def fake_payload(b: dict, _data_dir) -> dict:
        return {"chart": [{"time": c["time"], "value": c["close"]} for c in ohlcv], "ohlcv": ohlcv}

    with patch("trendalgo.ta.prewarm.bot_chart_payload", side_effect=fake_payload):
        label = _prewarm_one(tmp_path, bot)
    assert "BTC/USD" in label
    assert get_ta_signal_cache().stats.misses_full >= 1


def test_trim_readonly_frame_copies_before_mutation() -> None:
    from trendalgo.ta.frame_cache import ATTR_READONLY

    ohlcv = _ohlcv(900)
    df = ohlcv_list_to_df(ohlcv, pair="BTC/USD", fetch_tf="60")
    assert df.attrs.get(ATTR_READONLY) is True
    bot = _bot(timeframe="60")
    preset = resolve_preset("RSI", {"timeperiod": 14})
    trimmed = trim_df_for_bot(df, preset, bot)
    assert len(trimmed) < len(df)
    assert trimmed is not df


def test_stale_fallback_on_signature_change() -> None:
    cache = TaSignalCache()
    bot = _bot()
    base = _ohlcv(80)
    cache.get_or_compute_signals(ohlcv_list_to_df(base), base, bot)
    shifted = _ohlcv(81, start_ts=base[0]["time"] + 60)
    cache.get_or_compute_signals(ohlcv_list_to_df(shifted), shifted, bot)
    assert cache.stats.stale_fallback >= 1


def test_ohlcv_cascade_invalidation_clears_frame_cache() -> None:
    from trendalgo.constants.timeframes import timeframe_for_fetch
    from trendalgo.ta.frame_cache import get_frame_cache

    ohlcv = _ohlcv(40)
    fetch_tf = timeframe_for_fetch("60")
    ohlcv_list_to_df(ohlcv, pair="BTC/USD", fetch_tf=fetch_tf)
    assert get_frame_cache().stats_payload()["entries"] >= 1
    get_ta_signal_cache().coordinator.on_ohlcv_signature_change("BTC/USD", "60")
    stats = get_ta_signal_cache().stats_payload()
    assert stats["invalidations_ohlcv"] >= 1
    assert get_frame_cache().stats_payload()["entries"] == 0
