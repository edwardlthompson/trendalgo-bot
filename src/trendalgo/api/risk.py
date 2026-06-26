"""HTTP-ready risk metrics (FastAPI wiring in Sprint 3)."""

from __future__ import annotations

from trendalgo.risk.manager import RiskManager
from trendalgo.risk.metrics import metrics_summary


def get_risk_status(
    manager: RiskManager, open_exposure_usd: float = 0.0
) -> dict[str, float | bool | str]:
    return metrics_summary(manager, open_exposure_usd)
