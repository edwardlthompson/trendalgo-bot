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
    version: str = "2"
    generated_at: datetime
    as_of: datetime
    scan_id: int
    degraded: bool = False
    opportunities: list[OpportunityRow] = Field(default_factory=list)

    model_config = {"extra": "forbid"}

    def to_contract_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "generated_at": self.generated_at.isoformat(),
            "as_of": self.as_of.isoformat(),
            "scan_id": self.scan_id,
            "degraded": self.degraded,
            "opportunities": [o.model_dump() for o in self.opportunities],
        }
