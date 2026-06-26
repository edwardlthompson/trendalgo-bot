from datetime import UTC, datetime

from trendalgo.ai.backtest_summary import analyze_backtest, rule_based_summary
from trendalgo.schemas.backtest_result import BacktestResult, BacktestTradeSummary


def _result() -> BacktestResult:
    now = datetime.now(UTC)
    trades = [
        BacktestTradeSummary(
            pair="BTC/USD",
            profit_ratio=0.01,
            profit_abs=10,
            open_date=now,
            close_date=now,
        )
    ]
    return BacktestResult(
        strategy="multi-tf-example",
        pair="BTC/USD",
        timeframe="5m",
        timerange="20240101-",
        total_trades=1,
        profit_total=10,
        profit_total_pct=0.01,
        max_drawdown=0.01,
        trades=trades,
    )


def test_rule_based_summary() -> None:
    text = rule_based_summary(_result())
    assert "multi-tf-example" in text
    assert "$10.00" in text


def test_analyze_backtest_defaults_rule_based() -> None:
    out = analyze_backtest(_result())
    assert out["engine"] == "rule-based"
    assert "summary" in out
