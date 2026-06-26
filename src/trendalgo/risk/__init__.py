"""Risk management — sizing, caps, circuit breaker, journal."""

from trendalgo.risk.config import RiskLimits
from trendalgo.risk.journal import TradeJournal, TradeRecord
from trendalgo.risk.manager import RiskManager, RiskState
from trendalgo.risk.metrics import metrics_summary, risk_metrics
from trendalgo.risk.protections import build_protections, merge_risk_into_config, validate_pre_live
from trendalgo.risk.strategy_mixins import RiskGuardMixin

__all__ = [
    "RiskLimits",
    "RiskManager",
    "RiskState",
    "RiskGuardMixin",
    "TradeJournal",
    "TradeRecord",
    "build_protections",
    "merge_risk_into_config",
    "validate_pre_live",
    "metrics_summary",
    "risk_metrics",
]
