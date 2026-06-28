"""pandas-ta-classic compute smoke tests."""

from __future__ import annotations

import pandas as pd
import pytest

from trendalgo.ta.pandas_ta_catalog import pandas_ta_available
from trendalgo.ta.pandas_ta_engine import compute_pandas_ta


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


@pytest.mark.skipif(not pandas_ta_available(), reason="pandas-ta-classic not installed")
def test_supertrend_via_pandas_ta() -> None:
    out = compute_pandas_ta("SUPERTREND", _sample_df(), length=7)
    assert "value" in out or any(k.startswith("supert") for k in out)
