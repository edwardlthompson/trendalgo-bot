"""Live dashboard WebSocket — pushes risk + bot snapshots."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from trendalgo.api.risk import get_risk_status

router = APIRouter()


def _snapshot(app_state: Any) -> dict[str, Any]:
    return {
        "type": "snapshot",
        "dry_run": app_state.bot.dry_run,
        "equity_usd": app_state.bot.equity_usd,
        "pair": app_state.bot.pair,
        "risk": get_risk_status(app_state.risk_manager),
    }


@router.websocket("/ws/live")
async def live_ws(websocket: WebSocket) -> None:
    await websocket.accept()
    state = websocket.app.state.trendalgo
    try:
        while True:
            await websocket.send_text(json.dumps(_snapshot(state)))
            await asyncio.sleep(2.0)
    except WebSocketDisconnect:
        return
