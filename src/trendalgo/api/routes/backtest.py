from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from trendalgo.ai.insights import expanded_insights
from trendalgo.analytics.metrics import compute_metrics, equity_curve
from trendalgo.api.backtest_runner import run_sample_backtest
from trendalgo.backtest.attribution import attribute_signals
from trendalgo.backtest.slippage import apply_slippage
from trendalgo.scanner.backtest import BacktestDataLoader

router = APIRouter()


class BacktestRequest(BaseModel):
    strategy: str = "multi-tf-example"
    pair: str = "BTC/USD"
    timeframe: str = "5m"
    timerange: str = "20240101-20240201"
    slippage_pct: float = Field(0, ge=0, le=0.05)
    fee_pct: float = Field(0, ge=0, le=0.05)
    save_to_library: bool = True
    tag: str | None = None

    model_config = {"extra": "forbid"}


@router.post("/backtest")
def trigger_backtest(body: BacktestRequest, request: Request) -> dict[str, Any]:
    state = request.app.state.trendalgo
    loader = BacktestDataLoader(state.scanner_store.latest_snapshot())
    pair = body.pair
    timerange = body.timerange
    if pair == "BTC/USD" and loader.snapshot and loader.snapshot.opportunities:
        pair = loader.pairs_for_backtest(1)[0]
        timerange = loader.suggested_timerange()
    result = run_sample_backtest(
        strategy=body.strategy,
        pair=pair,
        timeframe=body.timeframe,
        timerange=timerange,
    )
    if body.slippage_pct or body.fee_pct:
        result = apply_slippage(result, body.slippage_pct, body.fee_pct)
    metrics = compute_metrics(result.trades)
    curve = equity_curve(result.trades)
    attribution = attribute_signals(result.model_dump(), scanner_active=True)
    analysis = expanded_insights(result, attribution)
    payload = {
        "result": result.model_dump(mode="json"),
        "metrics": metrics.__dict__,
        "equity_curve": curve,
        "analysis": analysis,
        "attribution": attribution,
    }
    state.last_backtest = payload
    if body.save_to_library:
        run_id = state.backtest_library.save(body.strategy, pair, payload, tag=body.tag)
        payload["library_id"] = run_id
    state.log(f"backtest complete: {body.strategy} {pair} pnl={result.profit_total}")
    return payload


@router.get("/backtest/latest")
def latest_backtest(request: Request) -> dict[str, Any]:
    state = request.app.state.trendalgo
    if state.last_backtest is None:
        return {"result": None, "metrics": None, "equity_curve": []}
    return state.last_backtest
