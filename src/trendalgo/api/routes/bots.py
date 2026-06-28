from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from trendalgo.bots.chart import bot_chart_payload, bot_close_chart
from trendalgo.bots.chart_regions import trade_highlight_regions
from trendalgo.bots.chart_trades import trades_to_chart_markers
from trendalgo.bots.equity_limits import (
    bot_equity_limits,
    normalize_equity_mode,
    resolve_equity_usd,
    validate_equity_input,
)
from trendalgo.bots.limits import limits_payload, validate_bot_capacity
from trendalgo.bots.sim_trades import simulated_trades_for_bot
from trendalgo.bots.summary import bot_pnl_breakdown, enrich_bots_with_market
from trendalgo.constants.timeframes import (
    TRADINGVIEW_INTERVAL_LABELS,
    TRADINGVIEW_INTERVALS,
    normalize_tv_interval,
)
from trendalgo.market.warmup import cache_status_for_bots, get_warmup_runner
from trendalgo.ta.cache import get_ta_signal_cache
from trendalgo.ta.catalog import all_ta_names
from trendalgo.ta.param_specs import ta_param_specs
from trendalgo.ta.prewarm import get_ta_prewarm_runner
from trendalgo.templates.import_export import list_param_specs
from trendalgo.templates.registry import get
from trendalgo.trading.multi_exchange import route_order

router = APIRouter()


class AddBotBody(BaseModel):
    label: str = Field(..., min_length=1)
    strategy_id: str = "RSI"
    pair: str = "BTC/USD"
    equity_usd: float = 1000.0
    exchange: str = "kraken"
    timeframe: str = "60"
    enabled: bool = False
    ta_params: dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "forbid"}


class BotEnabledBody(BaseModel):
    enabled: bool

    model_config = {"extra": "forbid"}


class UpdateBotBody(BaseModel):
    label: str = Field(..., min_length=1)
    strategy_id: str
    pair: str
    exchange: str = "kraken"
    equity_usd: float = Field(..., gt=0)
    equity_mode: Literal["base", "quote", "portfolio_pct", "usd", "pct", "manual"] = "quote"
    equity_input: float | None = Field(default=None, gt=0)
    timeframe: str = "60"
    ta_params: dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "forbid"}


class ForceTradeBody(BaseModel):
    side: Literal["buy", "sell"]
    amount: float | None = Field(default=None, gt=0)

    model_config = {"extra": "forbid"}


def _data_dir() -> Path:
    import os

    return Path(os.environ.get("TRENDALGO_DATA_DIR", "data"))


def _default_force_amount(pair: str, equity_usd: float) -> float:
    base = pair.split("/")[0].upper()
    if base == "BTC":
        return 0.001
    if base == "ETH":
        return 0.01
    return max(0.001, round(equity_usd / 10_000, 6))


def _enrich_bots(state: Any, bots: list[dict[str, Any]]) -> list[dict[str, Any]]:

    return enrich_bots_with_market(bots, state.trade_journal, _data_dir())


def _bot_chart_payload(bot: dict[str, Any]) -> dict[str, Any]:
    return bot_chart_payload(bot, _data_dir())


def _bot_chart(bot: dict[str, Any]) -> list[dict[str, int | float]]:
    return bot_close_chart(bot, _data_dir())


def _mark_price(chart: list[dict[str, int | float]]) -> float | None:
    if not chart:
        return None
    return float(chart[-1]["value"])


def _resolve_equity_usd(state: Any, body: UpdateBotBody, *, mark: float | None) -> float:
    mode = normalize_equity_mode(body.equity_mode)
    amount = float(body.equity_input or body.equity_usd)
    return resolve_equity_usd(
        state, body.pair, mode, amount, float(body.equity_usd), mark_price=mark
    )


def _param_specs_for_strategy(strategy_id: str) -> list[dict[str, Any]]:
    if strategy_id in all_ta_names():
        return [s.model_dump() for s in ta_param_specs(strategy_id)]
    template = get(strategy_id)
    if template:
        return [s.model_dump() for s in list_param_specs(strategy_id)]
    return [s.model_dump() for s in ta_param_specs(strategy_id)]


def _merged_strategy_params(
    bot: dict[str, Any], specs: list[dict[str, Any]]
) -> dict[str, float | int]:
    stored = dict(bot.get("ta_params") or {})
    merged: dict[str, float | int] = {}
    for spec in specs:
        key = str(spec["key"])
        default = spec.get("default", 0)
        val = stored.get(key, default)
        merged[key] = float(val) if isinstance(val, (int, float)) else default
    return merged


def _backtest_top5(state: Any, bot: dict[str, Any]) -> list[dict[str, Any]]:
    sweep = state.last_ta_sweep
    if not sweep:
        return []
    if str(sweep.get("pair", "")).upper() != str(bot["pair"]).upper():
        return []
    return list(sweep.get("top5") or sweep.get("rankings", [])[:5])


@router.get("/bots")
def list_bots(request: Request) -> dict[str, Any]:
    state = request.app.state.trendalgo
    bots = _enrich_bots(state, state.bot_orchestrator.list_bots())
    return {"bots": bots, "enabled_count": sum(1 for b in bots if b["enabled"])}


@router.get("/bots/limits")
def get_bot_limits(request: Request) -> dict[str, Any]:
    state = request.app.state.trendalgo
    bots = state.bot_orchestrator.list_bots()
    payload = limits_payload(paper=bool(state.bot.dry_run))
    payload["bot_count"] = len(bots)
    payload["enabled_count"] = sum(1 for b in bots if b["enabled"])
    return payload


@router.get("/bots/ohlcv/cache")
def get_bot_ohlcv_cache(request: Request) -> dict[str, Any]:
    """Coverage stats for OHLCV SQLite cache — bot pairs/timeframes only."""
    state = request.app.state.trendalgo
    bots = state.bot_orchestrator.list_bots()
    return cache_status_for_bots(_data_dir(), bots)


@router.post("/bots/ohlcv/warmup")
def start_bot_ohlcv_warmup(request: Request) -> dict[str, Any]:
    """Download or incrementally refresh OHLCV for all bot pair/timeframe series."""
    state = request.app.state.trendalgo
    bots = state.bot_orchestrator.list_bots()
    runner = get_warmup_runner(_data_dir())
    job = runner.start(bots)
    state.log(f"ohlcv warmup started: {job.get('total_series', 0)} series")
    return job


@router.get("/bots/ohlcv/warmup/active")
def get_active_ohlcv_warmup(request: Request) -> dict[str, Any]:
    runner = get_warmup_runner(_data_dir())
    snap = runner.snapshot()
    return snap or {"status": "idle", "progress_pct": 0, "messages": []}


@router.get("/bots/ta-cache/stats")
def get_ta_cache_stats() -> dict[str, Any]:
    """In-memory TA signal cache counters — hits, misses, invalidations."""
    return get_ta_signal_cache().stats_payload()


@router.post("/bots/ta-cache/prewarm")
def start_ta_cache_prewarm(request: Request) -> dict[str, Any]:
    """Precompute TA signals for unique bot fingerprints (background)."""
    state = request.app.state.trendalgo
    bots = state.bot_orchestrator.list_bots()
    runner = get_ta_prewarm_runner(_data_dir())
    job = runner.start(bots)
    state.log(f"ta prewarm started: {job.get('total_fingerprints', 0)} fingerprints")
    return job


@router.get("/bots/ta-cache/prewarm/active")
def get_active_ta_prewarm() -> dict[str, Any]:
    runner = get_ta_prewarm_runner(_data_dir())
    snap = runner.snapshot()
    return snap or {"status": "idle", "progress_pct": 0, "messages": []}


@router.get("/bots/{bot_id}")
def get_bot_detail(
    bot_id: int,
    request: Request,
    include_sim_trades: int = Query(
        1,
        ge=0,
        le=1,
        alias="trades",
        description="Set 0 to skip simulated trade TA compute",
    ),
) -> dict[str, Any]:
    state = request.app.state.trendalgo
    bot = state.bot_orchestrator.get_bot(bot_id)
    if bot is None:
        raise HTTPException(status_code=404, detail="bot not found")
    chart_payload = _bot_chart_payload(bot)
    chart = chart_payload["chart"]
    ohlcv = chart_payload["ohlcv"]
    mark = _mark_price(chart)
    breakdown = bot_pnl_breakdown(state.trade_journal, bot_id, chart=chart, current_price=mark)
    journal_trades = state.trade_journal.list_trades_for_bot(bot_id)
    if include_sim_trades:
        sim_trades, ta_cache_meta = simulated_trades_for_bot(
            bot, ohlcv, chart=chart, return_meta=True
        )
    else:
        sim_trades = []
        ta_cache_meta = None
    equity = float(bot["equity_usd"])
    total = float(breakdown["pnl_usd"])
    specs = _param_specs_for_strategy(str(bot["strategy_id"]))
    trade_markers = trades_to_chart_markers(journal_trades)
    sim_markers = trades_to_chart_markers(sim_trades)
    limits = bot_equity_limits(state, str(bot["pair"]), paper=bool(state.bot.dry_run))
    payload: dict[str, Any] = {
        "bot": {
            **bot,
            "timeframe": normalize_tv_interval(str(bot.get("timeframe") or "60")),
            "equity_mode": normalize_equity_mode(str(bot.get("equity_mode"))),
        },
        "realized_pnl_usd": float(breakdown["realized_pnl_usd"]),
        "unrealized_pnl_usd": float(breakdown["unrealized_pnl_usd"]),
        "pnl_usd": total,
        "pnl_pct": (total / equity) if equity > 0 else 0.0,
        "trade_count": int(breakdown["trade_count"]),
        "trades": journal_trades,
        "simulated_trades": sim_trades,
        "chart": chart,
        "ohlcv": ohlcv,
        "trade_markers": trade_markers,
        "simulated_markers": sim_markers,
        "trade_regions": trade_highlight_regions(trade_markers, ohlcv),
        "simulated_regions": trade_highlight_regions(sim_markers, ohlcv),
        "equity_limits": limits,
        "strategy_params": _merged_strategy_params(bot, specs),
        "available_timeframes": list(TRADINGVIEW_INTERVALS),
        "timeframe_labels": TRADINGVIEW_INTERVAL_LABELS,
        "param_specs": specs,
        "backtest_top5": _backtest_top5(state, bot),
    }
    if ta_cache_meta is not None:
        payload["ta_cache_meta"] = ta_cache_meta.to_dict()
    return payload


@router.get("/bots/{bot_id}/equity-limits")
def get_bot_equity_limits(bot_id: int, request: Request) -> dict[str, Any]:
    state = request.app.state.trendalgo
    bot = state.bot_orchestrator.get_bot(bot_id)
    if bot is None:
        raise HTTPException(status_code=404, detail="bot not found")
    return bot_equity_limits(state, str(bot["pair"]), paper=bool(state.bot.dry_run))


@router.post("/bots")
def add_bot(body: AddBotBody, request: Request) -> dict[str, Any]:
    state = request.app.state.trendalgo
    orch = state.bot_orchestrator
    paper = bool(state.bot.dry_run)
    bots = orch.list_bots()
    tf = normalize_tv_interval(body.timeframe)
    try:
        validate_bot_capacity(bots, paper=paper, adding=True, enabling=body.enabled, timeframe=tf)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    bot_id = orch.add_bot(
        body.label,
        body.strategy_id,
        body.pair,
        body.equity_usd,
        engine="native",
        exchange=body.exchange,
        timeframe=tf,
        enabled=body.enabled,
        ta_params=body.ta_params,
    )
    state.bot.bot_count = orch.count_enabled()
    state.log(f"bot added: {body.label}")
    return {"id": bot_id, "bots": _enrich_bots(state, orch.list_bots())}


@router.put("/bots/{bot_id}")
def update_bot(bot_id: int, body: UpdateBotBody, request: Request) -> dict[str, Any]:
    orch = request.app.state.trendalgo.bot_orchestrator
    if orch.get_bot(bot_id) is None:
        raise HTTPException(status_code=404, detail="bot not found")
    state = request.app.state.trendalgo
    mode = normalize_equity_mode(body.equity_mode)
    amount = float(body.equity_input or body.equity_usd)
    try:
        validate_equity_input(
            state,
            body.pair,
            mode,
            amount,
            paper=bool(state.bot.dry_run),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    chart = _bot_chart({"pair": body.pair, "timeframe": body.timeframe})
    equity_usd = _resolve_equity_usd(state, body, mark=_mark_price(chart))
    tf = normalize_tv_interval(body.timeframe)
    existing = orch.get_bot(bot_id) or {}
    enabled = bool(existing.get("enabled", True))
    try:
        validate_bot_capacity(
            orch.list_bots(),
            paper=bool(state.bot.dry_run),
            timeframe=tf,
            exclude_bot_id=bot_id,
            enabling=enabled,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    updated_row = {
        **existing,
        "label": body.label,
        "strategy_id": body.strategy_id,
        "pair": body.pair,
        "equity_usd": equity_usd,
        "timeframe": normalize_tv_interval(body.timeframe),
        "exchange": body.exchange,
        "equity_mode": mode,
        "equity_input": amount,
        "ta_params": body.ta_params,
    }
    get_ta_signal_cache().invalidate_for_bot_config_change(existing, updated_row)
    orch.update_bot(
        bot_id,
        label=body.label,
        strategy_id=body.strategy_id,
        pair=body.pair,
        equity_usd=equity_usd,
        timeframe=normalize_tv_interval(body.timeframe),
        exchange=body.exchange,
        equity_mode=mode,
        equity_input=amount,
        ta_params=body.ta_params,
    )
    request.app.state.trendalgo.log(f"bot updated: {body.label}")
    return {"bots": _enrich_bots(state, orch.list_bots())}


@router.delete("/bots/{bot_id}")
def delete_bot(bot_id: int, request: Request) -> dict[str, Any]:
    state = request.app.state.trendalgo
    orch = state.bot_orchestrator
    bot = orch.get_bot(bot_id)
    if bot is None:
        raise HTTPException(status_code=404, detail="bot not found")
    try:
        orch.delete_bot(bot_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    state.bot.bot_count = orch.count_enabled()
    state.log(f"bot deleted: {bot['label']}")
    return {"bots": _enrich_bots(state, orch.list_bots())}


@router.put("/bots/{bot_id}/enabled")
def set_bot_enabled(bot_id: int, body: BotEnabledBody, request: Request) -> dict[str, Any]:
    state = request.app.state.trendalgo
    orch = state.bot_orchestrator
    bot = orch.get_bot(bot_id)
    if bot is None:
        raise HTTPException(status_code=404, detail="bot not found")
    if body.enabled:
        try:
            validate_bot_capacity(
                orch.list_bots(),
                paper=bool(state.bot.dry_run),
                enabling=True,
                timeframe=str(bot.get("timeframe") or "60"),
                exclude_bot_id=bot_id,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    orch.set_enabled(bot_id, body.enabled)
    state.bot.bot_count = state.bot_orchestrator.count_enabled()
    return {"bots": _enrich_bots(state, state.bot_orchestrator.list_bots())}


@router.post("/bots/{bot_id}/force")
def force_bot_trade(bot_id: int, body: ForceTradeBody, request: Request) -> dict[str, Any]:
    state = request.app.state.trendalgo
    bot = state.bot_orchestrator.get_bot(bot_id)
    if bot is None:
        raise HTTPException(status_code=404, detail="bot not found")
    amount = body.amount or _default_force_amount(str(bot["pair"]), float(bot["equity_usd"]))
    try:
        result = route_order(
            str(bot["exchange"]),
            str(bot["pair"]),
            body.side,
            amount,
            dry_run=state.bot.dry_run,
            control=state.exchange_control,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    state.log(f"force {body.side} bot {bot['label']} amount={amount}")
    return {"bot_id": bot_id, "side": body.side, "amount": amount, "order": result}
