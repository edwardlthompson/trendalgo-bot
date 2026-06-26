from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse

from trendalgo.export.hub import export_bundle, export_hub_manifest, export_settings_json
from trendalgo.export.tax import tax_csv

router = APIRouter()


@router.get("/export/hub")
def export_hub(request: Request) -> dict[str, Any]:
    return export_hub_manifest(request.app.state.trendalgo)


@router.get("/export/bundle")
def export_bundle_route(request: Request) -> dict[str, Any]:
    return export_bundle(request.app.state.trendalgo)


@router.get("/export/settings")
def export_settings(request: Request) -> dict[str, Any]:
    return export_settings_json(request.app.state.trendalgo)


@router.get("/export/tax")
def export_tax_csv(request: Request) -> PlainTextResponse:
    state = request.app.state.trendalgo
    trades = state.trade_journal.list_trades()
    if not trades and state.last_backtest and state.last_backtest.get("result"):
        trades = state.last_backtest["result"].get("trades", [])
    csv_text = tax_csv(trades)
    return PlainTextResponse(csv_text, media_type="text/csv")
