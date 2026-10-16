"""Compare our TA compute path to TA-Lib / published Wilder formulas."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from trendalgo.ta.engine import compute, talib_available

pytestmark = pytest.mark.skipif(not talib_available(), reason="TA-Lib required")


def _ohlcv(n: int = 200) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    close = 100 + np.cumsum(rng.normal(0, 1, n))
    idx = pd.date_range("2024-01-01", periods=n, freq="h", tz="UTC")
    high = close + rng.uniform(0.2, 1.5, n)
    low = close - rng.uniform(0.2, 1.5, n)
    open_ = close + rng.normal(0, 0.3, n)
    volume = rng.uniform(100, 1000, n)
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
        index=idx,
    )


def test_rsi_matches_talib_wilder() -> None:
    import talib

    df = _ohlcv()
    ours = compute("RSI", df, timeperiod=14)["value"]
    ref = talib.RSI(df["close"].to_numpy(dtype=float), timeperiod=14)
    mask = np.isfinite(ours) & np.isfinite(ref)
    assert mask.sum() > 50
    assert np.allclose(ours[mask], ref[mask], rtol=1e-9, atol=1e-9)


def test_macd_matches_talib() -> None:
    import talib

    df = _ohlcv()
    out = compute("MACD", df, fastperiod=12, slowperiod=26, signalperiod=9)
    macd, signal, hist = talib.MACD(
        df["close"].to_numpy(dtype=float), fastperiod=12, slowperiod=26, signalperiod=9
    )
    for key, ref in (("macd", macd), ("signal", signal), ("hist", hist)):
        ours = out[key]
        mask = np.isfinite(ours) & np.isfinite(ref)
        assert mask.sum() > 20
        assert np.allclose(ours[mask], ref[mask], rtol=1e-9, atol=1e-9)


def test_bbands_middle_is_sma() -> None:
    import talib

    df = _ohlcv()
    out = compute("BBANDS", df, timeperiod=20, nbdevup=2, nbdevdn=2)
    upper, mid, lower = talib.BBANDS(
        df["close"].to_numpy(dtype=float), timeperiod=20, nbdevup=2, nbdevdn=2
    )
    mask = np.isfinite(out["middle"]) & np.isfinite(mid)
    assert np.allclose(out["middle"][mask], mid[mask], rtol=1e-9, atol=1e-9)
    assert np.allclose(out["upper"][mask], upper[mask], rtol=1e-9, atol=1e-9)
    assert np.allclose(out["lower"][mask], lower[mask], rtol=1e-9, atol=1e-9)


def test_atr_matches_talib_even_if_not_in_trade_pool() -> None:
    import talib

    df = _ohlcv()
    ours = compute("ATR", df, timeperiod=14)["value"]
    ref = talib.ATR(
        df["high"].to_numpy(dtype=float),
        df["low"].to_numpy(dtype=float),
        df["close"].to_numpy(dtype=float),
        timeperiod=14,
    )
    mask = np.isfinite(ours) & np.isfinite(ref)
    assert mask.sum() > 50
    assert np.allclose(ours[mask], ref[mask], rtol=1e-9, atol=1e-9)


def test_manual_wilder_rsi_agrees_with_engine() -> None:
    """Investopedia / Wilder RSI: SMA seed then RMA gains/losses."""
    df = _ohlcv(180)
    period = 14
    close = df["close"].to_numpy(dtype=float)
    delta = np.diff(close, prepend=close[0])
    gains = np.where(delta > 0, delta, 0.0)
    losses = np.where(delta < 0, -delta, 0.0)
    avg_g = np.full_like(close, np.nan)
    avg_l = np.full_like(close, np.nan)
    avg_g[period] = gains[1 : period + 1].mean()
    avg_l[period] = losses[1 : period + 1].mean()
    for i in range(period + 1, len(close)):
        avg_g[i] = (avg_g[i - 1] * (period - 1) + gains[i]) / period
        avg_l[i] = (avg_l[i - 1] * (period - 1) + losses[i]) / period
    rs = avg_g / np.where(avg_l == 0, np.nan, avg_l)
    manual = 100.0 - (100.0 / (1.0 + rs))
    ours = compute("RSI", df, timeperiod=period)["value"]
    mask = np.isfinite(manual) & np.isfinite(ours)
    # Allow small seed-index differences vs TA-Lib unstable period.
    assert mask.sum() > 40
    assert float(np.nanmedian(np.abs(manual[mask] - ours[mask]))) < 2.0
