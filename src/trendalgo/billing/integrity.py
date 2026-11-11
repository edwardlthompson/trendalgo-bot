"""Server-side statement recompute and mismatch checks (BILL-04)."""

from __future__ import annotations

from typing import Any

from trendalgo.billing.eligibility import billable_from_iso
from trendalgo.billing.profit import rollup_period
from trendalgo.billing.rules import apply_monthly_rules
from trendalgo.billing.schema import DEFAULT_LICENSE_RATE
from trendalgo.billing.statements import build_statement
from trendalgo.billing.store import BillingStore
from trendalgo.risk.journal import TradeJournal


def recompute_statement_from_journal(
    billing: BillingStore,
    journal: TradeJournal,
    *,
    period: str,
    persist: bool = True,
) -> dict[str, Any]:
    """Recompute from journal fills — never trust a client-supplied net."""
    enrollment = billing.get_enrollment()
    rate = float(enrollment.get("license_rate_pct", DEFAULT_LICENSE_RATE))
    share_class = str(enrollment.get("share_class") or "alpha")
    if share_class not in ("alpha", "standard"):
        share_class = "alpha"
    billable_from = billable_from_iso(enrollment)
    trades = [
        t
        for t in journal.list_trades(limit=2**31 - 1)
        if str(t.get("created_at", "")).startswith(period)
        or (t.get("created_at") and str(t["created_at"])[:7] == period)
    ]
    # Prefer venue fill timestamps when present
    for trade in trades:
        if trade.get("fill_ts"):
            trade["created_at"] = trade["fill_ts"]
    rows, result = apply_monthly_rules(
        trades,
        rate,
        deficit_usd=0.0,
        billable_from=billable_from,
        share_class=share_class,  # type: ignore[arg-type]
    )
    rollup = rollup_period(rows, bh_net_usd=result.bh_net_usd)
    statement = build_statement(
        period,
        rollup,
        rows,
        bh_net_usd=result.bh_net_usd,
        excess_usd=result.excess_usd,
        rate_pct=rate,
        floor_applied=result.floor_applied,
        cap_applied=result.cap_applied,
        share_class=share_class,
    )
    if persist:
        billing.upsert_statement(period, statement)
        billing.upsert_ledger_rows(period, rows)
    return statement


def statement_mismatch(stored: dict[str, Any], recomputed: dict[str, Any]) -> bool:
    keys = ("gross_profit_usd", "license_fee_usd", "bh_net_usd", "excess_usd")
    for key in keys:
        if round(float(stored.get(key) or 0), 2) != round(float(recomputed.get(key) or 0), 2):
            return True
    return str(stored.get("signed_hash") or "") != str(recomputed.get("signed_hash") or "")
