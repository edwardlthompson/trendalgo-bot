"""Fee rules — carry-forward, drawdown pause (M3, M4, M12)."""

from __future__ import annotations

from typing import Any

from trendalgo.billing.profit import license_fee_for_trade


def _zero_fee_item(t: dict[str, Any], pnl: float, rule: str) -> dict[str, Any]:
    return {
        "trade_ref": t.get("exchange_trade_id", ""),
        "pair": t.get("pair", ""),
        "gross_profit_usd": pnl,
        "license_fee_usd": 0.0,
        "net_benefit_usd": pnl,
        "rule_applied": rule,
        "exchange": t.get("exchange", ""),
        "bot_id": t.get("bot_id"),
    }


def apply_fee_rules(
    trades: list[dict[str, Any]],
    rate_pct: float,
    *,
    carry_forward_credit_usd: float = 0.0,
    drawdown_paused: bool = False,
    billable_from: str | None = None,
) -> tuple[list[dict[str, Any]], float]:
    """Return ledger line items and remaining carry-forward credit."""
    items: list[dict[str, Any]] = []
    credit = carry_forward_credit_usd

    if drawdown_paused:
        for t in trades:
            pnl = float(t.get("pnl_usd", 0))
            items.append(
                {
                    "trade_ref": t.get("exchange_trade_id", ""),
                    "pair": t.get("pair", ""),
                    "gross_profit_usd": pnl,
                    "license_fee_usd": 0.0,
                    "net_benefit_usd": pnl,
                    "rule_applied": "drawdown_pause",
                    "exchange": t.get("exchange", ""),
                    "bot_id": t.get("bot_id"),
                }
            )
        return items, credit

    for t in trades:
        pnl = float(t.get("pnl_usd", 0))
        trade_at = str(t.get("created_at") or "")
        if billable_from is None:
            items.append(_zero_fee_item(t, pnl, "awaiting_first_profit"))
            continue
        if trade_at and trade_at < billable_from:
            items.append(_zero_fee_item(t, pnl, "billing_trial_period"))
            continue
        calc = license_fee_for_trade(pnl, rate_pct)
        fee = calc.license_fee_usd
        if fee > 0 and credit > 0:
            applied = min(fee, credit)
            fee = round(fee - applied, 2)
            credit = round(credit - applied, 2)
            rule = "carry_forward_applied"
        else:
            rule = calc.rule_applied
        items.append(
            {
                "trade_ref": t.get("exchange_trade_id", ""),
                "pair": t.get("pair", ""),
                "gross_profit_usd": pnl,
                "license_fee_usd": fee,
                "net_benefit_usd": round(pnl - fee, 2),
                "rule_applied": rule,
                "exchange": t.get("exchange", ""),
                "bot_id": t.get("bot_id"),
            }
        )
    return items, credit
