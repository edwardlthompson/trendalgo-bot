from typing import Any

from fastapi import APIRouter, BackgroundTasks, Query, Request
from pydantic import BaseModel, Field

from trendalgo.api.state import AppState
from trendalgo.lts_vendor.public_snapshot import load_public_snapshot, relay_health
from trendalgo.scanner.config import ScannerSettings
from trendalgo.scanner.host_filters import load_host_filters, save_host_filters
from trendalgo.scanner.pipeline import run_pipeline
from trendalgo.scanner.progress import get_scan_progress
from trendalgo.scanner.scheduler import run_scheduled_scan
from trendalgo.scanner.watchlist_bridge import pairs_for_bot_whitelist

router = APIRouter()


class PinPairBody(BaseModel):
    pair: str = Field(..., min_length=3)

    model_config = {"extra": "forbid"}


class DisplayFiltersBody(BaseModel):
    exchanges: list[str] = Field(default_factory=list)
    gain7Text: str = ""
    gain30Text: str = ""

    model_config = {"extra": "forbid"}


@router.get("/scanner/snapshot")
def scanner_snapshot(request: Request) -> dict[str, Any]:
    state: AppState = request.app.state.trendalgo
    snap = state.scanner_store.latest_snapshot()
    if snap is None:
        return {
            "version": "2",
            "generated_at": None,
            "as_of": None,
            "scan_id": 0,
            "degraded": True,
            "opportunities": [],
        }
    return snap.to_contract_dict()


@router.post("/scanner/run")
def scanner_run(request: Request) -> dict[str, Any]:
    state: AppState = request.app.state.trendalgo
    scan_id = run_scheduled_scan(state.scanner_store, state.log)
    snap = state.scanner_store.latest_snapshot()
    body = snap.to_contract_dict() if snap else {"scan_id": scan_id, "opportunities": []}
    body["scan_id"] = scan_id
    return body


@router.get("/scanner/settings")
def scanner_get_settings(request: Request) -> dict[str, Any]:
    state: AppState = request.app.state.trendalgo
    settings = state.scanner_store.get_settings()
    return settings.model_dump()


@router.get("/scanner/display-filters")
def scanner_get_display_filters() -> dict[str, Any]:
    """Host LTS display filters (exchanges + gain text); survives desktop relaunches."""
    return load_host_filters()


@router.put("/scanner/display-filters")
def scanner_put_display_filters(body: DisplayFiltersBody) -> dict[str, Any]:
    return save_host_filters(body.model_dump())


@router.put("/scanner/settings")
def scanner_put_settings(body: ScannerSettings, request: Request) -> dict[str, Any]:
    state: AppState = request.app.state.trendalgo
    saved = state.scanner_store.save_settings(body)
    interval_sec = max(60, int(saved.interval_minutes) * 60)
    try:
        from trendalgo.lts_vendor.public_snapshot import patch_scan_interval_seconds

        patch_scan_interval_seconds(interval_sec)
    except Exception as exc:
        state.log(f"scanner snapshot interval patch failed: {exc}")
    sched = state.scanner_scheduler
    minutes = max(60, int(saved.interval_minutes))
    try:
        from apscheduler.triggers.interval import IntervalTrigger

        reschedule = getattr(sched, "reschedule_job", None)
        if callable(reschedule):
            reschedule("trendalgo-scanner", trigger=IntervalTrigger(minutes=minutes))
        else:
            add_job = getattr(sched, "add_job", None)
            if callable(add_job):
                add_job(
                    lambda: run_scheduled_scan(state.scanner_store, state.log),
                    "interval",
                    minutes=minutes,
                    id="trendalgo-scanner",
                    replace_existing=True,
                    coalesce=True,
                    max_instances=1,
                )
        state.log(f"scanner interval rescheduled to {minutes}m")
    except Exception as exc:
        state.log(f"scanner interval reschedule failed: {exc}")
    return saved.model_dump()


@router.get("/scanner/watchlist")
def scanner_watchlist(request: Request) -> dict[str, list[str]]:
    pairs = request.app.state.trendalgo.scanner_store.watchlist()
    return {"pairs": pairs}


@router.post("/scanner/watchlist")
def scanner_pin(request: Request, body: PinPairBody) -> dict[str, list[str]]:
    store = request.app.state.trendalgo.scanner_store
    store.pin_pair(body.pair)
    return {"pairs": store.watchlist()}


@router.get("/scanner/pairs-for-bot")
def scanner_pairs_for_bot(request: Request) -> dict[str, list[str]]:
    store = request.app.state.trendalgo.scanner_store
    return {"pairs": pairs_for_bot_whitelist(store)}


@router.post("/scanner/preview")
def scanner_preview(request: Request) -> dict[str, Any]:
    """Dry-run pipeline without persisting (settings form preview)."""
    store = request.app.state.trendalgo.scanner_store
    settings = store.get_settings()
    snap = run_pipeline(settings, sample=True)
    return snap.to_contract_dict()


@router.get("/scanner/qualified_public_snapshot.json")
def scanner_qualified_public_snapshot() -> dict[str, Any]:
    """LTS dashboard contract — coins may include backtest_top_strategies / backtest_buy_hold."""
    return load_public_snapshot()


@router.get("/scanner/relay-health")
def scanner_relay_health() -> dict[str, Any]:
    """Stub relay health for the vendored LTS dashboard strip."""
    return relay_health()


@router.post("/scanner/backtest/run")
def scanner_backtest_run(
    request: Request,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    """Trigger LTS strategy sweep from latest v2 snapshot (background)."""
    state: AppState = request.app.state.trendalgo
    snap = state.scanner_store.latest_snapshot()
    if snap is None:
        return {"ok": False, "reason": "no_snapshot"}

    def _job() -> None:
        from trendalgo.lts_vendor.bridge import publish_from_v2_snapshot

        progress = get_scan_progress()
        progress.begin_job("Backtest")
        try:
            publish_from_v2_snapshot(snap, run_backtests=True)
        except Exception as exc:
            progress.log(f"Backtest job failed: {exc}", level="error")
        finally:
            progress.end_job()

    background_tasks.add_task(_job)
    return {"ok": True, "queued": True, "opportunities": len(snap.opportunities)}


@router.get("/scanner/progress")
def scanner_progress(after: int = Query(0, ge=0)) -> dict[str, Any]:
    """Live scan/backtest run state plus activity lines newer than ``after`` (poll loop)."""
    return get_scan_progress().snapshot(after=after)
