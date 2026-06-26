from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from trendalgo.backtest.hyperopt import trigger_hyperopt

router = APIRouter()


class HyperoptBody(BaseModel):
    strategy: str = "multi-tf-example"
    pair: str = "BTC/USD"
    epochs: int = Field(50, ge=10, le=500)

    model_config = {"extra": "forbid"}


@router.post("/hyperopt")
def run_hyperopt(body: HyperoptBody, request: Request) -> dict[str, Any]:
    result = trigger_hyperopt(body.strategy, body.pair, body.epochs)
    request.app.state.trendalgo.log(f"hyperopt queued: {body.strategy}")
    return result
