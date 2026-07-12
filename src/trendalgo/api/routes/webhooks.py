from typing import Any

from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse

from trendalgo.signals.runner_bridge import bridge_tradingview_signal
from trendalgo.signals.tradingview import TradingViewWebhook

router = APIRouter()


@router.post("/webhooks/telegram")
async def telegram_webhook(
    request: Request,
    x_telegram_secret: str | None = Header(
        default=None,
        alias="X-Telegram-Bot-Api-Secret-Token",
    ),
) -> JSONResponse:
    state = request.app.state.trendalgo
    try:
        update = await request.json()
    except ValueError:
        return JSONResponse({"accepted": False, "reason": "invalid json"}, status_code=400)
    if not isinstance(update, dict):
        return JSONResponse({"accepted": False, "reason": "invalid update"}, status_code=400)
    status, result = state.telegram_ingress.handle(
        update,
        state.risk_manager,
        secret=x_telegram_secret,
    )
    state.log(
        f"telegram ingress: {result['reason']}" if not result["accepted"] else "telegram command"
    )
    return JSONResponse(result, status_code=status)


@router.post("/webhooks/tradingview")
async def tradingview_webhook(
    request: Request,
    x_signature: str | None = Header(default=None, alias="X-Signature"),
) -> dict[str, Any]:
    state = request.app.state.trendalgo
    body = await request.body()
    client_ip = request.client.host if request.client else "unknown"
    handler = TradingViewWebhook(state.portfolio_store)
    result = handler.handle(body, client_ip=client_ip, signature=x_signature)
    execution: dict[str, Any] | None = None
    if result.accepted and result.signal:
        execution = bridge_tradingview_signal(result.signal, state)
    return {
        "accepted": result.accepted,
        "reason": result.reason,
        "signal": result.signal,
        "execution": execution,
    }
