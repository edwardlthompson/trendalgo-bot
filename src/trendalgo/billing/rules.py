"""Monthly net fee rules — Alpha Share excess default (BILL-01/03, ADR-0017)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal

ShareClass = Literal["alpha", "standard"]

SHARE_ALPHA: ShareClass = "alpha"
SHARE_STANDARD: ShareClass = "standard"


def as_share_class(value: object) -> ShareClass:
    text = str(value or SHARE_ALPHA)
    if text == "standard":
        return SHARE_STANDARD
    return SHARE_ALPHA


FLOOR_USD = 5.0
PROFIT_CAP_PCT = 0.30
HARD_FEE_CEILING_USD = 10_000.0
DEFICIT_MAX_MONTHS = 6
PAUSE_PER_QUARTER = 1
HWM_RESET_PAID_STREAK = 18


@dataclass(frozen=True)
class MonthResult:
    net_usd: float
    fee_usd: float
    deficit_out_usd: float
    bh_net_usd: float = 0.0
    excess_usd: float = 0.0
    floor_applied: bool = False
    cap_applied: bool = False


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


def excess_usd(net_usd: float, bh_net: float) -> float:
    """Alpha Share basis: net minus non-negative buy-and-hold."""
    return round(net_usd - max(bh_net, 0.0), 2)


def apply_floor_and_cap(raw_fee: float, *, profit_usd: float) -> tuple[float, bool, bool]:
    """Lift-only $5 floor, then 30% profit cap and hard ceiling (BILL-03)."""
    if raw_fee <= 0:
        return 0.0, False, False
    floored = max(raw_fee, FLOOR_USD)
    floor_applied = floored > raw_fee + 1e-9
    capped = min(floored, HARD_FEE_CEILING_USD)
    if profit_usd > 0:
        capped = min(capped, round(profit_usd * PROFIT_CAP_PCT, 2))
    return round(capped, 2), floor_applied, capped + 1e-9 < floored


def monthly_fee(
    net_usd: float,
    deficit_usd: float,
    rate_pct: float,
    *,
    bh_net: float = 0.0,
    share_class: ShareClass = SHARE_ALPHA,
) -> tuple[float, float]:
    """Return (fee_usd, deficit_out_usd). Alpha bills excess; Standard bills equity."""
    result = compute_month_fee(
        net_usd, deficit_usd, rate_pct, bh_net=bh_net, share_class=share_class
    )
    return result.fee_usd, result.deficit_out_usd


def compute_month_fee(
    net_usd: float,
    deficit_usd: float,
    rate_pct: float,
    *,
    bh_net: float = 0.0,
    share_class: ShareClass = SHARE_ALPHA,
    drawdown_paused: bool = False,
) -> MonthResult:
    if deficit_usd < 0 or rate_pct < 0:
        raise ValueError("deficit and rate must not be negative")
    basis = excess_usd(net_usd, bh_net) if share_class == SHARE_ALPHA else round(net_usd, 2)
    if basis <= 0:
        return MonthResult(net_usd, 0.0, round(deficit_usd - basis, 2), bh_net, basis)
    recovered = min(basis, deficit_usd)
    raw = round((basis - recovered) * rate_pct, 2)
    fee, floor_applied, cap_applied = apply_floor_and_cap(raw, profit_usd=max(net_usd, 0.0))
    if drawdown_paused:
        fee, floor_applied, cap_applied = 0.0, False, False
    return MonthResult(
        net_usd,
        fee,
        round(deficit_usd - recovered, 2),
        bh_net,
        basis,
        floor_applied,
        cap_applied,
    )


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
    bh_net: float = 0.0,
    share_class: ShareClass = SHARE_ALPHA,
) -> tuple[list[dict[str, Any]], MonthResult]:
    """Ledger rows for one month. Each billed row carries its share of the month's fee."""
    if billable_from is None:
        waiting = [_row(t, 0.0, "awaiting_first_profit") for t in trades]
        return waiting, MonthResult(0.0, 0.0, deficit_usd, bh_net, 0.0)
    start = parse_utc(billable_from)
    billed = [_is_billed(t, start) for t in trades]
    net = round(sum(_pnl(t) for t, flag in zip(trades, billed, strict=True) if flag), 2)
    result = compute_month_fee(
        net,
        deficit_usd,
        rate_pct,
        bh_net=bh_net,
        share_class=share_class,
        drawdown_paused=drawdown_paused,
    )
    weights = [max(_pnl(t), 0.0) for t, flag in zip(trades, billed, strict=True) if flag]
    shares = iter(_allocate(result.fee_usd, weights))
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
    return rows, result


def age_deficit(deficit_usd: float, months_carried: int) -> float:
    """Drop deficit after DEFICIT_MAX_MONTHS (BILL-03)."""
    return 0.0 if months_carried >= DEFICIT_MAX_MONTHS else deficit_usd


def pause_allowed(pauses_used_this_quarter: int) -> bool:
    return pauses_used_this_quarter < PAUSE_PER_QUARTER


def should_reset_hwm(consecutive_paid: int) -> bool:
    return consecutive_paid >= HWM_RESET_PAID_STREAK


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
