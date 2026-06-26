from typing import Any

from fastapi import APIRouter, Header, Request

from trendalgo.signals.tradingview import TradingViewWebhook

router = APIRouter()


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
    if result.accepted and result.signal:
        state.log(f"tradingview signal: {result.signal}")
    return {"accepted": result.accepted, "reason": result.reason, "signal": result.signal}
