"""Scanner configuration."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ScannerSettings(BaseModel):
    interval_minutes: int = Field(60, ge=5, le=1440)
    min_volume_usd: float = Field(100000, gt=0)
    min_gain_pct: float = Field(0.02, ge=0)
    min_uniformity: float = Field(0.55, ge=0, le=1)
    universe_filter: str = "kraken-spot"
    trendspotter_boost: bool = True

    model_config = {"extra": "forbid"}
