"""Scanner configuration."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

# UI / scheduler allowed intervals (minutes). Minimum 1 hour.
ALLOWED_INTERVAL_MINUTES: tuple[int, ...] = (60, 120, 180, 240, 360, 480, 720, 1440)


def clamp_interval_minutes(raw: int) -> int:
    """Snap legacy or out-of-range values to the nearest allowed interval ≥ raw (min 60)."""
    try:
        minutes = int(raw)
    except (TypeError, ValueError):
        return 60
    if minutes in ALLOWED_INTERVAL_MINUTES:
        return minutes
    for allowed in ALLOWED_INTERVAL_MINUTES:
        if allowed >= minutes:
            return allowed
    return ALLOWED_INTERVAL_MINUTES[-1]


# Retained for LTS mixin / legacy prefs readers; board scan never gates on uniformity.
ALLOWED_UNIFORMITY: tuple[float, ...] = (0.15, 0.2, 0.25, 0.3, 0.35)


def clamp_min_uniformity(_raw: float) -> float:
    """Board scans ignore uniformity; always return 0 (gate off)."""
    return 0.0


class ScannerSettings(BaseModel):
    interval_minutes: int = Field(60, ge=60, le=1440)
    min_volume_usd: float = Field(100000, ge=0)
    min_gain_pct: float = Field(0.02, ge=0)
    # Optional early 7d floor from extended 1h bars (fraction). 0 = disabled.
    min_gain_7d_pct: float = Field(0.0, ge=0)
    # Unused on the board path (schema / DB compat); always coerced to 0.
    min_uniformity: float = Field(0.0, ge=0, le=1)
    # Drop pairs with any zero-volume/missing completed 1h bar in the last 24h.
    require_continuous_1h: bool = True
    universe_filter: str = "kraken-spot"
    trendspotter_boost: bool = True

    model_config = {"extra": "forbid"}

    @field_validator("interval_minutes", mode="before")
    @classmethod
    def _snap_interval(cls, value: Any) -> int:
        return clamp_interval_minutes(int(value) if value is not None else 60)

    @field_validator("min_uniformity", mode="before")
    @classmethod
    def _force_uniformity_off(cls, _value: Any) -> float:
        return 0.0


def default_scanner_settings() -> ScannerSettings:
    return ScannerSettings.model_validate({})
