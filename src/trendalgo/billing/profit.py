"""Period rollup of ledger rows (M1). Fees are set per month in rules.py (M7)."""

from __future__ import annotations

from typing import Any


def rollup_period(line_items: list[dict[str, Any]]) -> dict[str, float]:
    gross = sum(float(i.get("gross_profit_usd", 0)) for i in line_items)
    fees = sum(float(i.get("license_fee_usd", 0)) for i in line_items)
    net_benefit = sum(float(i.get("net_benefit_usd", 0)) for i in line_items)
    return {
        "gross_profit_usd": round(gross, 2),
        "license_fee_usd": round(fees, 2),
        "net_benefit_usd": round(net_benefit, 2),
    }
