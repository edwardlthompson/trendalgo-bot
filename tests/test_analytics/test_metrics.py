from datetime import UTC, datetime

from trendalgo.analytics.metrics import compute_metrics, equity_curve
from trendalgo.schemas.backtest_result import BacktestTradeSummary


def _trade(profit: float, day: int) -> BacktestTradeSummary:
    ts = datetime(2024, 1, day, tzinfo=UTC)
    return BacktestTradeSummary(
        pair="BTC/USD",
        profit_ratio=profit / 1000,
        profit_abs=profit,
        open_date=ts,
        close_date=ts,
    )


def test_compute_metrics_basic() -> None:
    trades = [_trade(20, 1), _trade(-10, 2), _trade(15, 3)]
    m = compute_metrics(trades)
    assert m.total_trades == 3
    assert m.profit_total == 25.0
    assert 0 <= m.win_rate <= 1
    assert m.max_drawdown >= 0


def test_equity_curve_points() -> None:
    trades = [_trade(10, 1), _trade(5, 2)]
    curve = equity_curve(trades)
    assert len(curve) == 2
    assert curve[-1]["value"] == 1015.0
