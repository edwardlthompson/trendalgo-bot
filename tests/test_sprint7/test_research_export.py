"""Sprint 7 research & export tests."""


from trendalgo.export.tax import fifo_tax_rows, tax_csv
from trendalgo.optimize.heatmap import hyperopt_heatmap_grid
from trendalgo.optimize.monte_carlo import monte_carlo_trade_shuffle
from trendalgo.optimize.portfolio_stress import portfolio_monte_carlo
from trendalgo.optimize.walk_forward import run_walk_forward
from trendalgo.portfolio.correlation import correlation_matrix, diversification_suggestions
from trendalgo.risk.exit_rules import ExitRules, scale_position_amount


def test_walk_forward_complete() -> None:
    result = run_walk_forward([10, -5, 8, 3, -2, 12])
    assert result["status"] == "complete"
    assert result["fold_count"] >= 1


def test_monte_carlo_intervals() -> None:
    mc = monte_carlo_trade_shuffle([10, -5, 8])
    assert mc["p5"] <= mc["p50"] <= mc["p95"]


def test_portfolio_stress() -> None:
    stress = portfolio_monte_carlo(1500, [0.01, -0.02, 0.005])
    assert stress["p50_usd"] > 0


def test_tax_fifo_csv() -> None:
    trades = [{"pair": "BTC/USD", "profit_abs": 12.0}]
    rows = fifo_tax_rows(trades)
    assert rows
    csv_text = tax_csv(trades)
    assert "realized_gl_usd" in csv_text


def test_correlation_and_diversification() -> None:
    matrix = correlation_matrix([{"asset": "BTC", "value_usd": 100}])
    assert matrix["assets"]
    tips = diversification_suggestions([{"asset": "BTC", "pct": 0.8}])
    assert tips


def test_exit_rules_and_heatmap() -> None:
    rules = ExitRules(trailing_stop_pct=0.04)
    assert rules.scale_out_enabled
    assert scale_position_amount(100, 0.5) == 50.0
    grid = hyperopt_heatmap_grid()
    assert grid["cells"]
