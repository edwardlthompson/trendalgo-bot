def test_uniform_score_short_dataframe() -> None:
    import pandas as pd

    from trendalgo.lts.mixins import TrendSpotterMixin

    class _Stub(TrendSpotterMixin):
        lts_lookback = 20

    mixin = _Stub()
    df = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=3, freq="h"),
            "open": [1, 2, 3],
            "high": [1, 2, 3],
            "low": [1, 2, 3],
            "close": [1, 2, 3],
            "volume": [1.0, 1.0, 1.0],
        }
    )
    assert mixin.lts_uniform_score(df) == 0.5
    assert mixin.lts_trend_bullish(df, threshold=0.9) is False
