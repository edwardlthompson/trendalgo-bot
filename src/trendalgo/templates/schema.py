"""Strategy template JSON schema (T9)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class TemplateParamSpec(BaseModel):
    key: str
    label: str
    type: str = "number"
    default: float | int | str | bool = 0
    min: float | None = None
    max: float | None = None

    model_config = {"extra": "forbid"}


class StrategyTemplateExport(BaseModel):
    id: str
    description: str
    module_path: str
    timeframes: list[str]
    kind: str = "custom"
    params: list[TemplateParamSpec] = Field(default_factory=list)
    param_values: dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "forbid"}
