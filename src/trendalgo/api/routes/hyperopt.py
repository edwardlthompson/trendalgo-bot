from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from trendalgo.backtest.hyperopt import get_hyperopt_job, trigger_hyperopt

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


@router.get("/hyperopt/{job_id}")
def hyperopt_status(job_id: str) -> dict[str, Any]:
    result = get_hyperopt_job(job_id)
    if result is None:
        raise HTTPException(status_code=404, detail="hyperopt job not found")
    return result
