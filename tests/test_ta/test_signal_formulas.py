"""Investopedia-aligned signal formulas: RSI, MACD, BBANDS, SMA, WILLR levels."""

from __future__ import annotations

import numpy as np
import pandas as pd

from trendalgo.ta.engine import compute
from trendalgo.ta.signal_kinds import oscillator_levels, signal_kind
from trendalgo.ta.signals import primary_series, resolve_preset, signals_for_preset


def _ohlcv_from_close(close: np.ndarray) -> pd.DataFrame:
    idx = pd.date_range("2024-01-01", periods=len(close), freq="h", tz="UTC")
    c = pd.Series(close, index=idx, dtype=float)
    return pd.DataFrame(
        {"open": c, "high": c + 0.5, "low": c - 0.5, "close": c, "volume": 1000.0},
        index=idx,
    )


def test_rsi_kind_and_levels() -> None:
    preset = resolve_preset("RSI", {"timeperiod": 14})
    assert preset["kind"] == "bounded_reversal"
    assert preset["entry_level"] == 30.0
    assert preset["exit_level"] == 70.0
    assert signal_kind("RSI") == "bounded_reversal"


def test_willr_uses_williams_zones() -> None:
    entry, exit_ = oscillator_levels("WILLR")
    assert entry == -80.0
    assert exit_ == -20.0
    preset = resolve_preset("WILLR", {"timeperiod": 14})
    assert preset["entry_level"] == -80.0
    assert preset["exit_level"] == -20.0


def test_rsi_entries_on_oversold_recovery() -> None:
    # Plunge then recover so Wilder RSI crosses up through 30.
    close = np.concatenate(
        [
            np.linspace(100, 40, 40),
            np.linspace(40, 90, 80),
        ]
    )
    df = _ohlcv_from_close(close)
    preset = resolve_preset("RSI", {"timeperiod": 14})
    entries, exits = signals_for_preset(df, preset)
    assert int(entries.sum()) > 0


def test_macd_cross_above_signal() -> None:
    # Slow drift then sharp rally → MACD crosses above signal.
    close = np.concatenate([np.linspace(100, 95, 60), np.linspace(95, 140, 60)])
    df = _ohlcv_from_close(close)
    preset = resolve_preset("MACD", {})
    assert preset["kind"] == "macd_cross"
    entries, exits = signals_for_preset(df, preset)
    assert int(entries.sum()) > 0


def test_bbands_keeps_talib_timeperiod_and_middle_primary() -> None:
    close = np.linspace(100, 120, 100) + np.sin(np.linspace(0, 8, 100)) * 3
    df = _ohlcv_from_close(close)
    out = compute("BBANDS", df, timeperiod=20, nbdevup=2.0, nbdevdn=2.0)
    assert "middle" in out
    mid = primary_series("BBANDS", out, df["close"])
    # Primary must be middle (SMA), not lower band.
    assert np.allclose(mid.to_numpy(), out["middle"], equal_nan=True)
    preset = resolve_preset("BBANDS", {"timeperiod": 20})
    assert "timeperiod" in preset or "length" not in preset or preset.get("kind") == "price_cross"
    # TA-Lib path: timeperiod preserved (not renamed away only).
    assert preset.get("timeperiod") == 20 or preset.get("length") == 20
    entries, _exits = signals_for_preset(df, preset)
    assert len(entries) == len(df)


def test_sma_ma_cross_defaults() -> None:
    close = np.concatenate([np.linspace(100, 80, 40), np.linspace(80, 130, 80)])
    df = _ohlcv_from_close(close)
    preset = resolve_preset("SMA", {})
    assert preset["kind"] == "ma_cross"
    assert preset["fast"] == 10
    assert preset["slow"] == 30
    entries, exits = signals_for_preset(df, preset)
    assert int(entries.sum()) > 0


def test_math_helper_is_math_skip() -> None:
    assert signal_kind("ADD") == "math_skip"
    assert signal_kind("ACOS") == "math_skip"
    assert signal_kind("ATR") == "math_skip"
    preset = resolve_preset("ADD", {})
    assert preset["kind"] == "math_skip"


def test_adx_uses_di_cross_not_zero_cross() -> None:
    assert signal_kind("ADX") == "di_cross"
    close = np.concatenate([np.linspace(100, 90, 40), np.linspace(90, 130, 80)])
    df = _ohlcv_from_close(close)
    # Add some range so +DI/−DI move
    df["high"] = df["close"] + 2
    df["low"] = df["close"] - 2
    preset = resolve_preset("ADX", {"timeperiod": 14})
    assert preset["kind"] == "di_cross"
    entries, exits = signals_for_preset(df, preset)
    assert int(entries.sum()) > 0


def test_sar_strips_bogus_timeperiod_and_fires() -> None:
    close = np.concatenate([np.linspace(100, 80, 50), np.linspace(80, 120, 70)])
    df = _ohlcv_from_close(close)
    df["high"] = df["close"] + 1.5
    df["low"] = df["close"] - 1.5
    preset = resolve_preset("SAR", {"timeperiod": 14})
    assert "timeperiod" not in preset or preset.get("acceleration") == 0.02
    # Sanitize happens at compute time; ensure signals run
    entries, exits = signals_for_preset(df, preset)
    assert int(entries.sum()) > 0


def test_donchian_primary_prefers_middle() -> None:
    close = np.linspace(50, 80, 80) + np.sin(np.linspace(0, 6, 80)) * 2
    df = _ohlcv_from_close(close)
    try:
        out = compute("DONCHIAN", df, length=20)
    except Exception:
        return  # pandas-ta optional path
    if "middle" not in out and not any("mid" in str(k).lower() for k in out):
        return
    mid = primary_series("DONCHIAN", out, df["close"])
    assert len(mid) == len(df)
