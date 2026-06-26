from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from trendalgo.risk.exit_rules import ExitRules
from trendalgo.templates.import_export import export_json, import_json, list_param_specs
from trendalgo.templates.registry import get, list_templates

router = APIRouter()


class StrategyParams(BaseModel):
    params: dict[str, Any] = Field(default_factory=dict)


class TemplateImportBody(BaseModel):
    json: str

    model_config = {"extra": "forbid"}


@router.get("/strategies")
def strategies() -> dict[str, list[dict[str, Any]]]:
    items = [
        {
            "id": t.id,
            "description": t.description,
            "timeframes": t.timeframes,
            "module_path": t.module_path,
            "kind": t.kind,
        }
        for t in list_templates()
    ]
    return {"strategies": items}


@router.get("/strategies/{strategy_id}/params")
def get_params(strategy_id: str, request: Request) -> dict[str, Any]:
    if get(strategy_id) is None:
        raise HTTPException(status_code=404, detail="strategy not found")
    state = request.app.state.trendalgo
    return {
        "strategy_id": strategy_id,
        "params": state.strategy_params,
        "param_specs": [s.model_dump() for s in list_param_specs(strategy_id)],
    }


@router.put("/strategies/{strategy_id}/params")
def put_params(strategy_id: str, body: StrategyParams, request: Request) -> dict[str, Any]:
    if get(strategy_id) is None:
        raise HTTPException(status_code=404, detail="strategy not found")
    state = request.app.state.trendalgo
    state.strategy_params.update(body.params)
    state.log(f"strategy params updated: {strategy_id}")
    return {"strategy_id": strategy_id, "params": state.strategy_params}


@router.get("/strategies/{strategy_id}/export")
def export_template(strategy_id: str, request: Request) -> dict[str, str]:
    if get(strategy_id) is None:
        raise HTTPException(status_code=404, detail="strategy not found")
    state = request.app.state.trendalgo
    return {"json": export_json(strategy_id, state.strategy_params)}


@router.post("/strategies/import")
def import_template(body: TemplateImportBody, request: Request) -> dict[str, Any]:
    tpl = import_json(body.json)
    if get(tpl.id) is None:
        raise HTTPException(status_code=400, detail="template id not registered")
    state = request.app.state.trendalgo
    state.strategy_params.update(tpl.param_values)
    state.log(f"template imported: {tpl.id}")
    return {"strategy_id": tpl.id, "params": state.strategy_params}


@router.get("/strategies/exit-rules")
def get_exit_rules(request: Request) -> dict[str, Any]:
    return request.app.state.trendalgo.exit_rules.model_dump()


@router.put("/strategies/exit-rules")
def put_exit_rules(body: ExitRules, request: Request) -> dict[str, Any]:
    request.app.state.trendalgo.exit_rules = body
    request.app.state.trendalgo.log("exit rules updated")
    return body.model_dump()
