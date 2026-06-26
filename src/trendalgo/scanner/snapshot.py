"""Qualified snapshot contract (O5)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class OpportunityRow(BaseModel):
    rank: int
    pair: str
    uniformity: float
    gain_pct: float
    volume_score: float
    entry_signal: bool
    sparkline: list[float] = Field(default_factory=list)

    model_config = {"extra": "forbid"}


class QualifiedSnapshot(BaseModel):
    version: str = "1"
    generated_at: datetime
    scan_id: int
    opportunities: list[OpportunityRow] = Field(default_factory=list)

    model_config = {"extra": "forbid"}

    def to_contract_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "generated_at": self.generated_at.isoformat(),
            "scan_id": self.scan_id,
            "opportunities": [o.model_dump() for o in self.opportunities],
        }
