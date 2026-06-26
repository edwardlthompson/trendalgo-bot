from typing import Any

from fastapi import APIRouter, Request

from trendalgo.api.risk import get_risk_status

router = APIRouter()


@router.get("/risk")
def risk_status(request: Request) -> dict[str, Any]:
    state = request.app.state.trendalgo
    return get_risk_status(state.risk_manager)


@router.post("/risk/pause")
def pause_trading(request: Request) -> dict[str, str | bool]:
    state = request.app.state.trendalgo
    state.risk_manager.pause()
    state.log("trading paused via API")
    return {"ok": True, "paused": True}


@router.post("/risk/resume")
def resume_trading(request: Request) -> dict[str, str | bool]:
    state = request.app.state.trendalgo
    state.risk_manager.resume()
    state.log("trading resumed via API")
    return {"ok": True, "paused": False}
