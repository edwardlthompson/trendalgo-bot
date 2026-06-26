"""Native runner protection plugins and pre-live validation."""

from __future__ import annotations

from typing import Any

from trendalgo.risk.config import RiskLimits


def build_protections(limits: RiskLimits) -> list[dict[str, Any]]:
    """Protection rules aligned with native runner / RiskLimits."""
    return [
        {
            "method": "StoplossGuard",
            "lookback_period_candles": 24,
            "trade_limit": 4,
            "stop_duration_candles": 4,
            "only_per_pair": False,
        },
        {
            "method": "CooldownPeriod",
            "stop_duration_candles": 2,
        },
        {
            "method": "MaxDrawdown",
            "lookback_period_candles": 48,
            "trade_limit": 20,
            "stop_duration_candles": 12,
            "max_allowed_drawdown": limits.circuit_breaker_drawdown_pct,
        },
    ]


def validate_pre_live(config: dict[str, Any], *, go_live_approved: bool = False) -> list[str]:
    """Block accidental live trading without go-live gate (R-003)."""
    errors: list[str] = []
    if config.get("dry_run", True) is not False:
        return errors
    if not go_live_approved:
        errors.append("dry_run=false requires go-live-gate approval (H-010/H-028)")
    if not config.get("exchange", {}).get("key"):
        errors.append("live mode requires exchange API key in .env")
    return errors


def merge_risk_into_config(
    config: dict[str, Any],
    limits: RiskLimits,
    *,
    go_live_approved: bool = False,
) -> dict[str, Any]:
    """Apply stake caps and protections to a native bot config dict."""
    errors = validate_pre_live(config, go_live_approved=go_live_approved)
    if errors:
        raise ValueError("; ".join(errors))
    merged = dict(config)
    merged["max_open_trades"] = limits.max_open_trades
    merged["stake_amount"] = min(
        float(merged.get("stake_amount", limits.max_stake_usd)), limits.max_stake_usd
    )
    merged["protections"] = build_protections(limits)
    return merged
