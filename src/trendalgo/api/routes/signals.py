from typing import Any

from fastapi import APIRouter, Header, Request

from trendalgo.signals.generic import GenericSignalWebhook

router = APIRouter()


@router.post("/signals/webhook")
async def generic_signal_webhook(
    request: Request,
    x_signature: str | None = Header(default=None, alias="X-Signature"),
) -> dict[str, Any]:
    state = request.app.state.trendalgo
    body = await request.body()
    handler = GenericSignalWebhook()
    result = handler.handle(body, signature=x_signature)
    if result.accepted and result.signal:
        state.log(f"signal webhook: {result.signal}")
    return {"accepted": result.accepted, "reason": result.reason, "signal": result.signal}
