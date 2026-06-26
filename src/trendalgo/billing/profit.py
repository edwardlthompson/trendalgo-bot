"""Per-trade profit and period rollup (M1)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TradeProfit:
    trade_ref: str
    pair: str
    gross_profit_usd: float
    license_fee_usd: float
    net_benefit_usd: float
    rule_applied: str


def license_fee_for_trade(gross_profit_usd: float, rate_pct: float) -> TradeProfit:
    """Net-loss trades incur $0 license fee."""
    if gross_profit_usd <= 0:
        return TradeProfit(
            trade_ref="",
            pair="",
            gross_profit_usd=gross_profit_usd,
            license_fee_usd=0.0,
            net_benefit_usd=gross_profit_usd,
            rule_applied="net_loss_zero",
        )
    fee = round(gross_profit_usd * rate_pct, 2)
    return TradeProfit(
        trade_ref="",
        pair="",
        gross_profit_usd=gross_profit_usd,
        license_fee_usd=fee,
        net_benefit_usd=round(gross_profit_usd - fee, 2),
        rule_applied="net_positive",
    )


def rollup_period(line_items: list[dict[str, Any]]) -> dict[str, float]:
    gross = sum(float(i.get("gross_profit_usd", 0)) for i in line_items)
    fees = sum(float(i.get("license_fee_usd", 0)) for i in line_items)
    net_benefit = sum(float(i.get("net_benefit_usd", 0)) for i in line_items)
    return {
        "gross_profit_usd": round(gross, 2),
        "license_fee_usd": round(fees, 2),
        "net_benefit_usd": round(net_benefit, 2),
    }
