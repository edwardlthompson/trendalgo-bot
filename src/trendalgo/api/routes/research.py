from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel

from trendalgo.optimize.heatmap import hyperopt_heatmap_grid
from trendalgo.optimize.monte_carlo import monte_carlo_trade_shuffle
from trendalgo.optimize.portfolio_stress import portfolio_monte_carlo
from trendalgo.optimize.walk_forward import walk_forward_from_backtest
from trendalgo.portfolio.correlation import correlation_matrix, diversification_suggestions
from trendalgo.portfolio.overview import build_portfolio_overview
from trendalgo.trading.backtest.walk_forward import run_native_walk_forward

router = APIRouter()


class WalkForwardBody(BaseModel):
    strategy: str = "multi-tf-example"
    pair: str = "BTC/USD"
    exchange_id: str = "kraken"
    use_native: bool = True

    model_config = {"extra": "forbid"}


@router.post("/research/walk-forward")
def research_walk_forward(body: WalkForwardBody, request: Request) -> dict[str, Any]:
    state = request.app.state.trendalgo
    if body.use_native:
        result = run_native_walk_forward(
            body.strategy, [], pair=body.pair, exchange_id=body.exchange_id
        )
        state.log(
            f"native walk-forward: {result['fold_count']} folds avg_test={result['avg_test_pnl']}"
        )
        return result
    trades: list[dict[str, Any]] = []
    if state.last_backtest and state.last_backtest.get("result"):
        trades = state.last_backtest["result"].get("trades", [])
    result = walk_forward_from_backtest(trades)
    result["engine"] = "sample"
    state.log(f"walk-forward: {result['fold_count']} folds")
    return result


@router.post("/research/monte-carlo")
def research_monte_carlo(request: Request) -> dict[str, Any]:
    state = request.app.state.trendalgo
    profits: list[float] = []
    if state.last_backtest and state.last_backtest.get("result"):
        profits = [
            float(t.get("profit_abs", 0)) for t in state.last_backtest["result"].get("trades", [])
        ]
    return monte_carlo_trade_shuffle(profits)


@router.post("/research/portfolio-monte-carlo")
def research_portfolio_mc(request: Request) -> dict[str, Any]:
    overview = build_portfolio_overview(request.app.state.trendalgo)
    curve = overview.get("equity_curve", [])
    daily_returns: list[float] = []
    if len(curve) >= 2:
        for i in range(1, len(curve)):
            prev = float(curve[i - 1]["total_usd"])
            cur = float(curve[i]["total_usd"])
            daily_returns.append((cur - prev) / prev if prev else 0.0)
    return portfolio_monte_carlo(float(overview["net_worth_usd"]), daily_returns)


@router.get("/research/correlation")
def research_correlation(request: Request) -> dict[str, Any]:
    overview = build_portfolio_overview(request.app.state.trendalgo)
    matrix = correlation_matrix(overview.get("holdings", []))
    tips = diversification_suggestions(overview.get("allocation", []))
    return {"correlation": matrix, "suggestions": tips}


@router.get("/research/hyperopt-heatmap")
def research_heatmap(request: Request) -> dict[str, Any]:
    return hyperopt_heatmap_grid()
