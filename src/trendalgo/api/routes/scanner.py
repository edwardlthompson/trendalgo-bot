from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from trendalgo.api.state import AppState
from trendalgo.scanner.config import ScannerSettings
from trendalgo.scanner.pipeline import run_pipeline
from trendalgo.scanner.scheduler import run_scheduled_scan
from trendalgo.scanner.watchlist_bridge import pairs_for_bot_whitelist

router = APIRouter()


class PinPairBody(BaseModel):
    pair: str = Field(..., min_length=3)

    model_config = {"extra": "forbid"}


@router.get("/scanner/snapshot")
def scanner_snapshot(request: Request) -> dict[str, Any]:
    state: AppState = request.app.state.trendalgo
    snap = state.scanner_store.latest_snapshot()
    if snap is None:
        return {"version": "1", "generated_at": None, "scan_id": 0, "opportunities": []}
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


@router.put("/scanner/settings")
def scanner_put_settings(body: ScannerSettings, request: Request) -> dict[str, Any]:
    state: AppState = request.app.state.trendalgo
    saved = state.scanner_store.save_settings(body)
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
    snap = run_pipeline(settings)
    return snap.to_contract_dict()
