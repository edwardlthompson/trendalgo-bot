from datetime import UTC, datetime

from trendalgo.schemas.backtest_result import BacktestResult, BacktestTradeSummary


def test_backtest_result_schema() -> None:
    result = BacktestResult(
        strategy="MultiTFExample",
        pair="BTC/USD",
        timeframe="5m",
        timerange="20240101-20240201",
        total_trades=1,
        profit_total=10.5,
        profit_total_pct=1.05,
        trades=[
            BacktestTradeSummary(
                pair="BTC/USD",
                profit_ratio=0.01,
                profit_abs=10.5,
                open_date=datetime(2024, 1, 2, tzinfo=UTC),
                close_date=datetime(2024, 1, 3, tzinfo=UTC),
            )
        ],
    )
    dumped = result.model_dump()
    assert dumped["strategy"] == "MultiTFExample"
    assert len(dumped["trades"]) == 1
