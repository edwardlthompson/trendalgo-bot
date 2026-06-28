import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request

from trendalgo.api.risk import get_risk_status
from trendalgo.billing.license_gate import check_license_gate
from trendalgo.bots.summary import enrich_bots_with_market

router = APIRouter()


def _data_dir() -> Path:
    return Path(os.environ.get("TRENDALGO_DATA_DIR", "data"))


@router.get("/dashboard")
def dashboard(request: Request) -> dict[str, Any]:
    state = request.app.state.trendalgo
    enrollment = state.billing_store.get_enrollment()
    license_status = state.billing_store.get_license_status()
    gate_ok, gate_reason = check_license_gate(enrollment, license_status, dry_run=state.bot.dry_run)
    risk = get_risk_status(state.risk_manager, open_exposure_usd=0.0)
    if not gate_ok:
        risk = {**risk, "can_trade": False, "block_reason": gate_reason, "license_suspended": True}
    else:
        risk = {**risk, "license_suspended": False}
    bot_count = state.bot_orchestrator.count_enabled()
    return {
        "dry_run": state.bot.dry_run,
        "equity_usd": state.bot.equity_usd,
        "open_trades": state.bot.open_trades,
        "open_orders": state.bot.open_orders,
        "bot_count": bot_count,
        "bots": enrich_bots_with_market(
            state.bot_orchestrator.list_bots(),
            state.trade_journal,
            _data_dir(),
        ),
        "strategy_id": state.bot.strategy_id,
        "pair": state.bot.pair,
        "risk": risk,
    }
