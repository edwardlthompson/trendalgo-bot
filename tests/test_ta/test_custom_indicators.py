"""Custom extended indicator compute smoke tests."""

from __future__ import annotations

import pandas as pd

from trendalgo.ta.custom_indicators import compute_custom


def _sample_df(rows: int = 80) -> pd.DataFrame:
    idx = pd.RangeIndex(rows)
    close = pd.Series(100 + idx * 0.1, index=idx, dtype=float)
    return pd.DataFrame(
        {
            "open": close - 0.2,
            "high": close + 0.5,
            "low": close - 0.5,
            "close": close,
            "volume": pd.Series(1000 + idx * 5, index=idx, dtype=float),
        }
    )


def test_fibonacci_retrace_returns_levels() -> None:
    out = compute_custom("FIB_RETRACE", _sample_df(), lookback=20)
    assert "level_618" in out
    assert "value" in out
    assert len(out["level_618"]) == 80
