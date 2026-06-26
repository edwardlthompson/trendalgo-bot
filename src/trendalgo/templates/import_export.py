"""Template import/export — operator presets only (T9)."""

from __future__ import annotations

import json

from trendalgo.templates.registry import get
from trendalgo.templates.schema import StrategyTemplateExport, TemplateParamSpec

_PARAM_SPECS: dict[str, list[TemplateParamSpec]] = {
    "multi-tf-example": [
        TemplateParamSpec(key="rsi_entry", label="RSI entry", default=35, min=10, max=50),
        TemplateParamSpec(key="rsi_exit", label="RSI exit", default=65, min=50, max=90),
        TemplateParamSpec(
            key="lts_uniform_min", label="LTS uniform min", default=0.55, min=0, max=1
        ),
    ],
    "smart-dca": [
        TemplateParamSpec(
            key="dca_interval_hours", label="DCA interval (h)", default=24, min=1, max=168
        ),
        TemplateParamSpec(
            key="dca_amount_usd", label="DCA amount USD", default=50, min=5, max=5000
        ),
        TemplateParamSpec(key="dip_pct", label="Dip buy %", default=0.03, min=0.01, max=0.2),
    ],
    "grid-trading": [
        TemplateParamSpec(key="grid_levels", label="Grid levels", default=5, min=2, max=20),
        TemplateParamSpec(
            key="grid_spacing_pct", label="Grid spacing %", default=0.02, min=0.005, max=0.1
        ),
        TemplateParamSpec(key="grid_size_usd", label="Order size USD", default=25, min=5, max=1000),
    ],
    "multi-tf-ta": [
        TemplateParamSpec(key="rsi_entry", label="RSI entry", default=30, min=10, max=50),
        TemplateParamSpec(key="ema_fast", label="EMA fast", default=12, min=5, max=50),
        TemplateParamSpec(key="ema_slow", label="EMA slow", default=26, min=10, max=100),
    ],
}


def export_template(
    template_id: str, param_values: dict[str, object] | None = None
) -> StrategyTemplateExport:
    tpl = get(template_id)
    if tpl is None:
        raise ValueError(f"template not found: {template_id}")
    specs = _PARAM_SPECS.get(template_id, [])
    return StrategyTemplateExport(
        id=tpl.id,
        description=tpl.description,
        module_path=tpl.module_path,
        timeframes=list(tpl.timeframes),
        kind=tpl.kind,
        params=specs,
        param_values=param_values or {},
    )


def export_json(template_id: str, param_values: dict[str, object] | None = None) -> str:
    return json.dumps(export_template(template_id, param_values).model_dump(), indent=2)


def import_json(raw: str) -> StrategyTemplateExport:
    data = json.loads(raw)
    return StrategyTemplateExport.model_validate(data)


def list_param_specs(template_id: str) -> list[TemplateParamSpec]:
    return _PARAM_SPECS.get(template_id, [])
