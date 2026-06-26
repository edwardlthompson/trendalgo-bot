from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

router = APIRouter()


class AddBotBody(BaseModel):
    label: str = Field(..., min_length=1)
    strategy_id: str
    pair: str
    equity_usd: float = 1000.0

    model_config = {"extra": "forbid"}


class BotEnabledBody(BaseModel):
    enabled: bool

    model_config = {"extra": "forbid"}


@router.get("/bots")
def list_bots(request: Request) -> dict[str, Any]:
    bots = request.app.state.trendalgo.bot_orchestrator.list_bots()
    return {"bots": bots, "enabled_count": sum(1 for b in bots if b["enabled"])}


@router.post("/bots")
def add_bot(body: AddBotBody, request: Request) -> dict[str, Any]:
    orch = request.app.state.trendalgo.bot_orchestrator
    bot_id = orch.add_bot(body.label, body.strategy_id, body.pair, body.equity_usd)
    request.app.state.trendalgo.bot.bot_count = orch.count_enabled()
    request.app.state.trendalgo.log(f"bot added: {body.label}")
    return {"id": bot_id, "bots": orch.list_bots()}


@router.put("/bots/{bot_id}/enabled")
def set_bot_enabled(bot_id: int, body: BotEnabledBody, request: Request) -> dict[str, Any]:
    state = request.app.state.trendalgo
    state.bot_orchestrator.set_enabled(bot_id, body.enabled)
    state.bot.bot_count = state.bot_orchestrator.count_enabled()
    return {"bots": state.bot_orchestrator.list_bots()}
