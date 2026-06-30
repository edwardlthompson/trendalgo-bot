"""TA compute engine fallbacks."""

from __future__ import annotations

import pandas as pd
import pytest

from trendalgo.ta.engine import _ensure_ohlcv, compute, compute_pandas, talib_available


def _sample_df(rows: int = 60) -> pd.DataFrame:
    idx = pd.RangeIndex(rows)
    close = pd.Series(100 + idx * 0.2, index=idx, dtype=float)
    return pd.DataFrame(
        {
            "open": close - 0.1,
            "high": close + 0.3,
            "low": close - 0.3,
            "close": close,
            "volume": pd.Series(1000 + idx, index=idx, dtype=float),
        }
    )


def test_ensure_ohlcv_requires_columns() -> None:
    with pytest.raises(ValueError, match="missing OHLCV"):
        _ensure_ohlcv(pd.DataFrame({"close": [1.0, 2.0]}))


def test_compute_pandas_indicators() -> None:
    df = _sample_df()
    ema = compute_pandas("EMA", df, timeperiod=5)
    rsi = compute_pandas("RSI", df, timeperiod=5)
    macd = compute_pandas("MACD", df)
    roc = compute_pandas("ROC", df, timeperiod=3)
    mom = compute_pandas("MOM", df, timeperiod=3)
    assert len(ema["value"]) == len(df)
    assert len(rsi["value"]) == len(df)
    assert set(macd) == {"macd", "signal", "hist"}
    assert len(roc["value"]) == len(df)
    assert len(mom["value"]) == len(df)


def test_compute_pandas_unknown_raises() -> None:
    with pytest.raises(KeyError, match="no pandas fallback"):
        compute_pandas("NOTREAL", _sample_df())


def test_compute_uses_cache_and_pandas_fallback() -> None:
    df = _sample_df()
    first = compute("SMA", df, timeperiod=5)
    second = compute("SMA", df, timeperiod=5)
    assert len(first["value"]) == len(df)
    assert len(second["value"]) == len(df)
    assert float(first["value"][-1]) == float(second["value"][-1])


def test_talib_available_is_bool() -> None:
    assert isinstance(talib_available(), bool)
