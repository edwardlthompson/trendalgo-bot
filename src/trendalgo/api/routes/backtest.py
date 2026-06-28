import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from trendalgo.ai.insights import expanded_insights
from trendalgo.analytics.metrics import compute_metrics, equity_curve
from trendalgo.api.backtest_runner import run_native_backtest_for_strategy, run_sample_backtest
from trendalgo.backtest.attribution import attribute_signals
from trendalgo.backtest.fleet_runner import FleetPreflightError, get_fleet_runner
from trendalgo.backtest.slippage import apply_slippage
from trendalgo.backtest.fleet_config import FLEET_LOOKBACK_DAYS, FLEET_LOOKBACK_SECONDS, fleet_lookback_seconds
from trendalgo.constants.timeframes import TRADINGVIEW_INTERVALS, TRADINGVIEW_INTERVAL_LABELS
from trendalgo.exchanges.fees import all_fee_schedules
from trendalgo.exchanges.fee_store import get_fee_store
from trendalgo.scanner.backtest import BacktestDataLoader
from trendalgo.strategies.runtime.loader import supported_strategy_ids

router = APIRouter()


def _data_dir() -> Path:
    return Path(os.environ.get("TRENDALGO_DATA_DIR", "data"))


def _sync_fleet_completion(state: Any, runner: Any) -> None:
    payload = runner.consume_completed()
    if not payload:
        return
    state.last_ta_fleet = payload
    state.last_ta_sweep = {
        "pair": payload["pair"],
        "exchange_id": payload["exchange_id"],
        "timeframe": (payload.get("best") or {}).get("timeframe"),
        "rankings": payload.get("rankings", []),
        "top5": payload.get("top5", []),
        "best": payload.get("best"),
    }
    best = payload.get("best") or {}
    state.log(
        f"ta-fleet {payload['pair']} {payload['exchange_id']}: "
        f"best={best.get('strategy_id')} net={best.get('net_profit')}"
    )


class BacktestRequest(BaseModel):
    strategy: str = "multi-tf-example"
    pair: str = "BTC/USD"
    timeframe: str = "5m"
    timerange: str = "20240101-20240201"
    slippage_pct: float = Field(0, ge=0, le=0.05)
    fee_pct: float = Field(0, ge=0, le=0.05)

    model_config = {"extra": "forbid"}


class FleetStartBody(BaseModel):
    exchange_id: str = "kraken"
    pair: str = "BTC/USD"
    stake_usd: float = Field(1000.0, gt=0, le=1_000_000)

    model_config = {"extra": "forbid"}


@router.get("/backtest/exchange-fees")
def exchange_fees() -> dict[str, Any]:
    schedules = all_fee_schedules()
    store = get_fee_store()
    return {
        "tier": schedules[0].tier if schedules else "retail_default",
        "exchanges": [s.to_dict() for s in schedules],
        "last_check": store.last_global_check(),
    }


@router.get("/backtest/fleet/lookbacks")
def fleet_lookbacks() -> dict[str, Any]:
    rows = [
        {
            "timeframe": tf,
            "label": TRADINGVIEW_INTERVAL_LABELS.get(tf, tf),
            "lookback_seconds": fleet_lookback_seconds(tf),
            "lookback_days": FLEET_LOOKBACK_DAYS,
        }
        for tf in TRADINGVIEW_INTERVALS
    ]
    return {
        "lookback_days": FLEET_LOOKBACK_DAYS,
        "lookback_seconds": FLEET_LOOKBACK_SECONDS,
        "uniform_window": True,
        "timeframes": rows,
    }


@router.post("/backtest/fleet")
def start_fleet_backtest(body: FleetStartBody, request: Request) -> dict[str, Any]:
    runner = get_fleet_runner(_data_dir())
    try:
        snap = runner.start(body.exchange_id, body.pair, body.stake_usd)
    except FleetPreflightError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    request.app.state.trendalgo.log(
        f"ta-fleet started: {body.exchange_id} {body.pair} stake={body.stake_usd}"
    )
    return snap


@router.get("/backtest/fleet/active")
def fleet_active(request: Request) -> dict[str, Any]:
    runner = get_fleet_runner(_data_dir())
    snap = runner.snapshot()
    if snap and snap.get("status") == "complete":
        _sync_fleet_completion(request.app.state.trendalgo, runner)
    return snap or {"status": "idle"}


@router.get("/backtest/fleet/latest")
def fleet_latest(
    request: Request,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    group_by: str | None = Query(None),
) -> dict[str, Any]:
    runner = get_fleet_runner(_data_dir())
    _sync_fleet_completion(request.app.state.trendalgo, runner)
    payload = runner.latest_from_store(limit=limit, offset=offset, group_by=group_by)
    if payload is None:
        cached = request.app.state.trendalgo.last_ta_fleet
        if cached:
            rankings = list(cached.get("rankings") or [])
            return {
                "job_id": cached.get("job_id"),
                "exchange_id": cached.get("exchange_id"),
                "pair": cached.get("pair"),
                "stake_usd": cached.get("stake_usd"),
                "summary": cached.get("summary", {}),
                "rankings": rankings[offset : offset + limit],
                "total_rankings": len(rankings),
                "limit": limit,
                "offset": offset,
            }
        return {"rankings": [], "total_rankings": 0}
    return payload


@router.get("/backtest/fleet/history")
def fleet_history(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    runner = get_fleet_runner(_data_dir())
    return runner.list_history(limit=limit, offset=offset)


@router.get("/backtest/fleet/history/{job_id}")
def fleet_history_run(job_id: str) -> dict[str, Any]:
    runner = get_fleet_runner(_data_dir())
    payload = runner.get_history_run(job_id)
    if payload is None:
        raise HTTPException(status_code=404, detail=f"fleet run not found: {job_id}")
    return payload


@router.post("/backtest")
def trigger_backtest(body: BacktestRequest, request: Request) -> dict[str, Any]:
    state = request.app.state.trendalgo
    loader = BacktestDataLoader(state.scanner_store.latest_snapshot())
    pair = body.pair
    timerange = body.timerange
    if pair == "BTC/USD" and loader.snapshot and loader.snapshot.opportunities:
        pair = loader.pairs_for_backtest(1)[0]
        timerange = loader.suggested_timerange()
    native_ids = set(supported_strategy_ids())
    if body.strategy in native_ids:
        result = run_native_backtest_for_strategy(
            strategy_id=body.strategy,
            pair=pair,
            timeframe=body.timeframe,
            timerange=timerange,
        )
    else:
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
    state.log(f"backtest complete: {body.strategy} {pair} pnl={result.profit_total}")
    return payload


@router.get("/backtest/latest")
def latest_backtest(request: Request) -> dict[str, Any]:
    state = request.app.state.trendalgo
    if state.last_backtest is None:
        return {"result": None, "metrics": None, "equity_curve": []}
    return state.last_backtest
