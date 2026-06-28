from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse

from trendalgo.portfolio.multi_exchange import sync_all_exchanges
from trendalgo.portfolio.overview import build_portfolio_overview, heatmap_rows
from trendalgo.portfolio.performance import build_performance_payload
from trendalgo.portfolio.snapshots import capture_portfolio_snapshot, run_daily_notification

router = APIRouter()


@router.get("/portfolio/overview")
def portfolio_overview(request: Request) -> dict[str, Any]:
    return build_portfolio_overview(request.app.state.trendalgo)


@router.get("/portfolio/performance")
def portfolio_performance(
    request: Request,
    range: str = Query("1y", alias="range", pattern="^(1y|6m|3m|1m|14d|7d|24h)$"),
) -> dict[str, Any]:
    state = request.app.state.trendalgo
    store = state.portfolio_store
    account_id = store.get_or_create_account("kraken", "default")
    try:
        payload = build_performance_payload(
            store,
            account_id,
            range,
            dry_run=state.bot.dry_run,
        )
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    payload["asset"] = "BTC"
    payload["quantity"] = 1.0
    return payload


@router.get("/portfolio/summary")
def portfolio_summary(request: Request) -> dict[str, Any]:
    store = request.app.state.trendalgo.portfolio_store
    account_id = store.get_or_create_account("kraken", "default")
    snap = store.latest_snapshot(account_id)
    return {"account_id": account_id, "latest": snap}


@router.get("/portfolio/history/{date}")
def portfolio_history(date: str, request: Request) -> dict[str, Any]:
    store = request.app.state.trendalgo.portfolio_store
    account_id = store.get_or_create_account("kraken", "default")
    snap = store.snapshot_by_date(account_id, date)
    return {"date": date, "snapshot": snap}


@router.get("/portfolio/heatmap")
def portfolio_heatmap(request: Request) -> dict[str, Any]:
    overview = build_portfolio_overview(request.app.state.trendalgo)
    return {"rows": heatmap_rows(overview["holdings"])}


@router.get("/portfolio/export")
def portfolio_export(request: Request) -> PlainTextResponse:
    store = request.app.state.trendalgo.portfolio_store
    account_id = store.get_or_create_account("kraken", "default")
    csv_text = store.export_holdings_csv(account_id)
    return PlainTextResponse(csv_text, media_type="text/csv")


@router.post("/portfolio/sync")
def portfolio_sync(request: Request) -> dict[str, Any]:
    state = request.app.state.trendalgo
    result = sync_all_exchanges(state.portfolio_store, dry_run=state.bot.dry_run)
    state.log(f"portfolio sync-all: {result.get('exchange_count')} venues mode={result.get('mode')}")
    return result


@router.post("/portfolio/snapshot")
def portfolio_snapshot_job(request: Request) -> dict[str, Any]:
    state = request.app.state.trendalgo
    return capture_portfolio_snapshot(
        state.portfolio_store,
        dry_run=state.bot.dry_run,
        on_log=state.log,
    )


@router.post("/portfolio/daily-notification")
def portfolio_daily_notification(request: Request) -> dict[str, Any]:
    state = request.app.state.trendalgo
    overview = build_portfolio_overview(state)
    sent = run_daily_notification(state.portfolio_store, overview, dry_run=state.bot.dry_run)
    return {"sent": sent, "preview": overview.get("daily_pnl_usd")}
