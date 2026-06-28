"""Exchange registry API routes (S13)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query, Request

from trendalgo.exchanges.fees import all_fee_schedules
from trendalgo.exchanges.fee_store import get_fee_store
from trendalgo.exchanges.fee_sync import sync_exchange_fees
from trendalgo.exchanges.registry import list_exchanges, load_registry
from trendalgo.exchanges.pairs import list_pairs_for_exchange
from trendalgo.constants.timeframes import TRADINGVIEW_INTERVALS, TRADINGVIEW_INTERVAL_LABELS

router = APIRouter()


@router.get("/exchanges/registry")
def exchanges_registry(_request: Request) -> dict[str, Any]:
    registry = load_registry()
    return {
        "version": registry.version,
        "exchanges": [entry.to_public_dict() for entry in list_exchanges()],
    }


@router.get("/exchanges/{exchange_id}/pairs")
def exchange_pairs(exchange_id: str) -> dict[str, Any]:
    pairs = list_pairs_for_exchange(exchange_id)
    return {"exchange_id": exchange_id, "pairs": pairs}


@router.get("/constants/timeframes")
def chart_timeframes() -> dict[str, Any]:
    return {
        "intervals": list(TRADINGVIEW_INTERVALS),
        "labels": TRADINGVIEW_INTERVAL_LABELS,
    }


@router.get("/exchanges/fees")
def exchange_fees_catalog() -> dict[str, Any]:
    schedules = all_fee_schedules()
    store = get_fee_store()
    return {
        "tier": schedules[0].tier if schedules else "retail_default",
        "exchanges": [s.to_dict() for s in schedules],
        "last_check": store.last_global_check(),
        "venue_count": len(schedules),
    }


@router.get("/exchanges/fees/checks")
def exchange_fee_checks(limit: int = Query(50, ge=1, le=200)) -> dict[str, Any]:
    store = get_fee_store()
    checks = store.recent_checks(limit=limit)
    return {"checks": checks, "total": len(checks), "last_check": store.last_global_check()}


@router.post("/exchanges/fees/sync")
def exchange_fees_sync(request: Request) -> dict[str, Any]:
    store = get_fee_store()
    summary = sync_exchange_fees(store, on_log=request.app.state.trendalgo.log)
    return summary
