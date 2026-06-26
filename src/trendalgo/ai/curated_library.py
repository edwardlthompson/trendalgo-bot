"""Operator-curated AI strategy library — versioned presets only (AI7)."""

from __future__ import annotations

from typing import Any

CURATED_VERSION = "2026.06.1"

CURATED_PRESETS: list[dict[str, Any]] = [
    {
        "id": "curated-lts-momentum",
        "version": CURATED_VERSION,
        "strategy_id": "strong-uptrend-scanner",
        "label": "LTS Momentum (curated)",
        "params": {"rsi_entry": 30, "lts_uniform_min": 0.6, "stoploss": -0.04},
        "operator_maintained": True,
    },
    {
        "id": "curated-steady-dca",
        "version": CURATED_VERSION,
        "strategy_id": "smart-dca",
        "label": "Steady DCA (curated)",
        "params": {"interval_hours": 12, "dip_boost_pct": 0.03},
        "operator_maintained": True,
    },
    {
        "id": "curated-range-grid",
        "version": CURATED_VERSION,
        "strategy_id": "grid-trading",
        "label": "Range Grid (curated)",
        "params": {"grid_levels": 5, "grid_spacing_pct": 0.015},
        "operator_maintained": True,
    },
]


def list_curated() -> dict[str, Any]:
    return {
        "version": CURATED_VERSION,
        "presets": CURATED_PRESETS,
        "user_uploads": False,
        "community_imports": False,
    }
