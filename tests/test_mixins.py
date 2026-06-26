import pandas as pd

from trendalgo.lts.mixins import TrendSpotterMixin


class _Stub(TrendSpotterMixin):
    lts_lookback = 5


def test_mixin_uniform_score() -> None:
    mixin = _Stub()
    df = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=10, freq="h"),
            "open": range(10),
            "high": range(10),
            "low": range(10),
            "close": range(10),
            "volume": [1.0] * 10,
        }
    )
    score = mixin.lts_uniform_score(df)
    assert 0.0 <= score <= 1.0
    assert mixin.lts_trend_bullish(df, threshold=0.5) is True
