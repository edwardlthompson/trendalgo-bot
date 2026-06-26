from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from trendalgo.backtest.compare import compare_runs

router = APIRouter()


class CompareBody(BaseModel):
    run_ids: list[int] = Field(..., min_length=1, max_length=5)

    model_config = {"extra": "forbid"}


class CloneBody(BaseModel):
    tag: str | None = None

    model_config = {"extra": "forbid"}


@router.get("/backtest/library")
def library_list(request: Request) -> dict[str, Any]:
    runs = request.app.state.trendalgo.backtest_library.list_runs()
    return {"runs": runs}


@router.get("/backtest/library/{run_id}")
def library_get(run_id: int, request: Request) -> dict[str, Any]:
    row = request.app.state.trendalgo.backtest_library.get(run_id)
    if row is None:
        raise HTTPException(status_code=404, detail="run not found")
    return row


@router.post("/backtest/library/{run_id}/clone")
def library_clone(run_id: int, body: CloneBody, request: Request) -> dict[str, Any]:
    lib = request.app.state.trendalgo.backtest_library
    new_id = lib.clone(run_id, body.tag)
    return {"id": new_id, "runs": lib.list_runs()}


@router.post("/backtest/library/{run_id}/share")
def library_share(run_id: int, request: Request) -> dict[str, Any]:
    lib = request.app.state.trendalgo.backtest_library
    row = lib.get(run_id)
    if row is None:
        raise HTTPException(status_code=404, detail="run not found")
    token = request.app.state.trendalgo.share_store.create_token(row["payload"])
    return {"token": token, "url": f"/api/v1/backtest/shared/{token}"}


@router.get("/backtest/shared/{token}")
def shared_backtest(token: str, request: Request) -> dict[str, Any]:
    payload = request.app.state.trendalgo.share_store.get(token)
    if payload is None:
        raise HTTPException(status_code=404, detail="share not found")
    return {"read_only": True, "payload": payload}


@router.post("/backtest/compare")
def backtest_compare(body: CompareBody, request: Request) -> dict[str, Any]:
    lib = request.app.state.trendalgo.backtest_library
    runs: list[dict[str, Any]] = []
    for rid in body.run_ids:
        row = lib.get(rid)
        if row:
            runs.append({"id": row["id"], **row["payload"]})
    return compare_runs(runs)
