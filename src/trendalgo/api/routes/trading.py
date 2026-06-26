from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from trendalgo.exchanges.pair_normalizer import normalize_pair
from trendalgo.exchanges.registry import get_entry, list_trading_exchanges, load_registry
from trendalgo.portfolio.arbitrage import detect_arbitrage_opportunities
from trendalgo.strategies.runtime.contract import Candle
from trendalgo.strategies.runtime.loader import load_strategy
from trendalgo.trading.multi_exchange import list_supported_exchanges, route_order
from trendalgo.trading.runner.adapters.registry import list_trading_adapter_ids
from trendalgo.trading.runner.dry_run import DryRunRunner

router = APIRouter()


def _require_trading_exchange(exchange_id: str) -> None:
    entry = get_entry(exchange_id)
    if not entry.trading_enabled:
        raise KeyError(f"exchange not enabled for trading: {exchange_id}")


class TickCandle(BaseModel):
    timestamp_ms: int
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0


class DryRunTickBody(BaseModel):
    strategy_id: str = "multi-tf-example"
    pair: str = "BTC/USD"
    exchange_id: str = "kraken"
    bot_id: int | None = None
    candle: TickCandle


class PauseBody(BaseModel):
    paused: bool


class RouteBody(BaseModel):
    pair: str
    side: str
    amount: float = Field(..., gt=0)


@router.get("/trading/runner/status")
def runner_status(request: Request) -> dict[str, Any]:
    state = request.app.state.trendalgo
    registry = load_registry()
    worldwide = [e.id for e in list_trading_exchanges() if e.us_restricted]
    return {
        "engine": "native",
        "mode": "dry-run-default" if state.bot.dry_run else "live",
        "exchanges": list_supported_exchanges(),
        "worldwide_trading_phase": registry.worldwide_trading_phase,
        "worldwide_exchanges": worldwide,
    }


@router.get("/trading/exchanges/control")
def exchange_control_status(request: Request) -> dict[str, Any]:
    state = request.app.state.trendalgo
    return {"exchanges": state.exchange_control.list_status()}


@router.put("/trading/exchanges/{exchange_id}/pause")
def exchange_pause(exchange_id: str, body: PauseBody, request: Request) -> dict[str, Any]:
    state = request.app.state.trendalgo
    if exchange_id not in list_supported_exchanges():
        raise HTTPException(status_code=404, detail="exchange not enabled for trading")
    state.exchange_control.set_paused(exchange_id, body.paused)
    row = state.exchange_control.get(exchange_id)
    return {"exchange": row}


@router.post("/trading/exchanges/{exchange_id}/go-live")
def exchange_go_live(exchange_id: str, request: Request) -> dict[str, Any]:
    state = request.app.state.trendalgo
    if exchange_id not in list_supported_exchanges():
        raise HTTPException(status_code=404, detail="exchange not enabled for trading")
    state.exchange_control.approve_go_live(exchange_id)
    state.log(f"go-live approved for {exchange_id}")
    return {"exchange": state.exchange_control.get(exchange_id)}


@router.post("/trading/exchanges/{exchange_id}/route")
def exchange_route(exchange_id: str, body: RouteBody, request: Request) -> dict[str, Any]:
    state = request.app.state.trendalgo
    try:
        return route_order(
            exchange_id,
            body.pair,
            body.side,
            body.amount,
            dry_run=state.bot.dry_run,
            control=state.exchange_control,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/trading/dry-run/tick")
def dry_run_tick(body: DryRunTickBody, request: Request) -> dict[str, Any]:
    state = request.app.state.trendalgo
    try:
        strategy = load_strategy(body.strategy_id)
        _require_trading_exchange(body.exchange_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    pair = normalize_pair(body.pair, body.exchange_id)
    runner = DryRunRunner(
        strategy=strategy,
        journal=state.trade_journal,
        exchange_id=body.exchange_id,
        pair=pair,
        wallet_usd=state.bot.equity_usd,
        bot_id=body.bot_id,
        control=state.exchange_control,
    )
    candle = Candle(
        timestamp_ms=body.candle.timestamp_ms,
        open=body.candle.open,
        high=body.candle.high,
        low=body.candle.low,
        close=body.candle.close,
        volume=body.candle.volume,
    )
    return runner.tick(candle)


@router.get("/trading/adapters")
def list_adapters() -> dict[str, list[str]]:
    return {"adapters": list_trading_adapter_ids()}


@router.get("/trading/arbitrage/signals")
def trading_arbitrage_signals(request: Request) -> dict[str, Any]:
    state = request.app.state.trendalgo
    result = detect_arbitrage_opportunities(dry_run=state.bot.dry_run)
    return {**result, "trading_lane": True}
