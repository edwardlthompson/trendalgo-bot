"""Monthly net fee rules with a high-water mark (ADR-0017 decision 4, register M7).

Each UTC calendar month nets the closed trades billed in that month. A positive net pays the rate
only on the part above the high-water mark. A losing month pays nothing and adds its loss to the
deficit. The deficit (the loss still to recover below the peak) carries into the next month.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True)
class MonthResult:
    net_usd: float
    fee_usd: float
    deficit_out_usd: float


def parse_utc(value: object) -> datetime | None:
    """Parse an ISO timestamp as UTC. Returns None when it cannot be read."""
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def monthly_fee(net_usd: float, deficit_usd: float, rate_pct: float) -> tuple[float, float]:
    """Return (fee_usd, deficit_out_usd) for one month's net realized profit."""
    if deficit_usd < 0 or rate_pct < 0:
        raise ValueError("deficit and rate must not be negative")
    if net_usd <= 0:
        return 0.0, round(deficit_usd - net_usd, 2)
    recovered = min(net_usd, deficit_usd)
    fee = round((net_usd - recovered) * rate_pct, 2)
    return fee, round(deficit_usd - recovered, 2)


def group_by_month(
    trades: list[dict[str, Any]], *, current_period: str
) -> dict[str, list[dict[str, Any]]]:
    """Group trades by UTC month. A trade with no readable time joins the current month."""
    groups: dict[str, list[dict[str, Any]]] = {}
    for trade in trades:
        parsed = parse_utc(trade.get("created_at"))
        key = parsed.strftime("%Y-%m") if parsed else current_period
        groups.setdefault(key, []).append(trade)
    return groups


def apply_monthly_rules(
    trades: list[dict[str, Any]],
    rate_pct: float,
    *,
    deficit_usd: float,
    drawdown_paused: bool = False,
    billable_from: str | None = None,
) -> tuple[list[dict[str, Any]], MonthResult]:
    """Ledger rows for one month. Each billed row carries its share of the month's fee."""
    if billable_from is None:  # awaiting the first profit: nothing billed, nothing carried
        waiting = [_row(t, 0.0, "awaiting_first_profit") for t in trades]
        return waiting, MonthResult(0.0, 0.0, deficit_usd)
    start = parse_utc(billable_from)
    billed = [_is_billed(t, start) for t in trades]
    net = round(sum(_pnl(t) for t, flag in zip(trades, billed, strict=True) if flag), 2)
    fee, deficit_out = monthly_fee(net, deficit_usd, rate_pct)
    charged = 0.0 if drawdown_paused else fee
    weights = [max(_pnl(t), 0.0) for t, flag in zip(trades, billed, strict=True) if flag]
    shares = iter(_allocate(charged, weights))
    rows: list[dict[str, Any]] = []
    for trade, flag in zip(trades, billed, strict=True):
        if not flag:
            rows.append(_row(trade, 0.0, "billing_trial_period"))
            continue
        share = next(shares)
        if drawdown_paused:
            rule = "drawdown_pause"
        else:
            rule = "monthly_net_fee_share" if share > 0 else "monthly_net_no_fee"
        rows.append(_row(trade, share, rule))
    return rows, MonthResult(net, charged, deficit_out)


def _pnl(trade: dict[str, Any]) -> float:
    return float(trade.get("pnl_usd") or 0)


def _is_billed(trade: dict[str, Any], start: datetime | None) -> bool:
    at = parse_utc(trade.get("created_at"))
    return at is not None and start is not None and at >= start


def _allocate(fee_usd: float, weights: list[float]) -> list[float]:
    """Split a fee in whole cents by weight. The shares add up to the fee exactly."""
    cents = round(fee_usd * 100)
    total = sum(weights)
    if cents <= 0 or total <= 0:
        return [0.0] * len(weights)
    exact = [cents * w / total for w in weights]
    whole = [math.floor(x) for x in exact]
    spare = cents - sum(whole)
    positive = [i for i, w in enumerate(weights) if w > 0]
    by_remainder = sorted(positive, key=lambda i: exact[i] - whole[i], reverse=True)
    for k in range(spare):
        whole[by_remainder[k % len(by_remainder)]] += 1
    return [c / 100 for c in whole]


def _row(trade: dict[str, Any], fee_usd: float, rule: str) -> dict[str, Any]:
    pnl = _pnl(trade)
    return {
        "trade_ref": trade.get("exchange_trade_id", ""),
        "pair": trade.get("pair", ""),
        "gross_profit_usd": pnl,
        "license_fee_usd": round(fee_usd, 2),
        "net_benefit_usd": round(pnl - fee_usd, 2),
        "rule_applied": rule,
        "exchange": trade.get("exchange", ""),
        "bot_id": trade.get("bot_id"),
    }
