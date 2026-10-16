"""Billing orchestration — process trades, statements, dashboard."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from trendalgo.billing.eligibility import (
    billable_from_iso,
    billing_is_active,
    eligibility_snapshot,
    sync_billing_eligibility,
)
from trendalgo.billing.license_gate import (
    check_license_gate,
    clear_grace,
    licensed_until_for_period,
    start_grace_period,
)
from trendalgo.billing.milestones import detect_milestones
from trendalgo.billing.payment_verifier import (
    create_payment_intent,
    enrich_payment_response,
    verify_pending_payment,
    watch_pending_payments,
)
from trendalgo.billing.profit import rollup_period
from trendalgo.billing.rules import apply_monthly_rules, group_by_month
from trendalgo.billing.schema import DEFAULT_LICENSE_RATE, GRACE_PERIOD_DAYS
from trendalgo.billing.settlement import list_available_assets
from trendalgo.billing.statements import build_statement
from trendalgo.billing.store import BillingStore
from trendalgo.risk.journal import TradeJournal, TradeRecord
from trendalgo.risk.manager import RiskManager


def _period_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m")


# The monthly chain needs every trade. list_trades() defaults to the newest 500.
ALL_TRADES = 2**31 - 1


def _write_statement(
    billing: BillingStore, period: str, items: list[dict[str, Any]], carry_usd: float
) -> None:
    rollup = rollup_period(items)
    statement = build_statement(period, rollup, items, carry_forward_credit_usd=carry_usd)
    billing.upsert_statement(period, statement)


def _start_grace_if_owed(
    billing: BillingStore, enrollment: dict[str, Any], period: str, fee_usd: float
) -> None:
    if fee_usd > 0 and enrollment.get("enrolled") and billing_is_active(enrollment):
        status = billing.get_license_status()
        billing.update_license_status(start_grace_period(status, period))


def seed_sample_trades(journal: TradeJournal) -> None:
    if journal.count_trades() > 0:
        return
    samples = [
        TradeRecord("BTC/USD", "long", 100, 25.0, "bot", "lts entry", "seed-1"),
        TradeRecord("ETH/USD", "long", 80, -12.0, "bot", "stop", "seed-2"),
        TradeRecord("BTC/USD", "long", 120, 40.0, "bot", "rsi exit", "seed-3"),
    ]
    for s in samples:
        try:
            journal.append_trade(s)
        except Exception:
            pass


def _attribution_by_exchange(items: list[dict[str, Any]]) -> dict[str, float]:
    totals: dict[str, float] = {}
    for item in items:
        key = str(item.get("exchange") or "unknown")
        totals[key] = round(totals.get(key, 0.0) + float(item.get("license_fee_usd", 0)), 2)
    return totals


def process_journal_trades(
    billing: BillingStore,
    journal: TradeJournal,
    risk_manager: RiskManager,
    *,
    period: str | None = None,
) -> dict[str, Any]:
    """Bill every month in order. Closed months are final; the open month is provisional."""
    period = period or _period_now()
    current = _period_now()
    sync_billing_eligibility(billing, journal)
    enrollment = billing.get_enrollment()
    rate = float(enrollment.get("license_rate_pct", DEFAULT_LICENSE_RATE))
    billable_from = billable_from_iso(enrollment)
    paused = bool(risk_manager.state.circuit_breaker_active)
    trades = [
        t
        for t in journal.list_trades(limit=ALL_TRADES)
        if float(t.get("pnl_usd", 0)) != 0 or t.get("signal_source") == "bot"
    ]
    by_month = group_by_month(trades, current_period=current)
    closed = billing.list_closed_periods()
    months = sorted(set(by_month) | set(closed) | {period})
    deficit = 0.0
    after: dict[str, float] = {}
    added = 0
    finalized: list[dict[str, Any]] = []
    late: list[str] = []
    for month in months:
        month_trades = by_month.get(month, [])
        if month in closed:  # final: never recalculated; a late trade is reported, not billed
            deficit = closed[month]
            known = billing.ledger_refs(month)
            refs = [str(t["exchange_trade_id"]) for t in month_trades]
            late += [ref for ref in refs if ref not in known]
            after[month] = deficit
            continue
        rows, result = apply_monthly_rules(
            month_trades,
            rate,
            deficit_usd=deficit,
            drawdown_paused=paused,
            billable_from=billable_from,
        )
        deficit = result.deficit_out_usd
        after[month] = deficit
        if month < current:
            added += billing.finalize_period(
                month,
                rows,
                net_usd=result.net_usd,
                fee_usd=result.fee_usd,
                deficit_out_usd=deficit,
            )
            finalized.append(
                {"period": month, "net_usd": result.net_usd, "license_fee_usd": result.fee_usd}
            )
            _start_grace_if_owed(billing, enrollment, month, result.fee_usd)
        else:
            added += billing.upsert_ledger_rows(month, rows)
        _write_statement(billing, month, rows, deficit)
    if billing.get_statement(period) is None:  # a closed month whose statement is missing
        _write_statement(
            billing,
            period,
            billing.list_ledger(period, limit=ALL_TRADES),
            after.get(period, deficit),
        )
    items = billing.list_ledger(period, limit=ALL_TRADES)
    return {
        "period": period,
        "trades_processed": added,
        "rollup": rollup_period(items),
        "attribution_by_exchange": _attribution_by_exchange(items),
        "billing_eligibility": eligibility_snapshot(enrollment),
        "finalized": finalized,
        "late_trades": sorted(set(late)),
    }


def build_dashboard(
    billing: BillingStore,
    risk_manager: RiskManager,
    *,
    dry_run: bool,
    journal: TradeJournal | None = None,
) -> dict[str, Any]:
    if journal is not None:
        sync_billing_eligibility(billing, journal)
    enrollment = billing.get_enrollment()
    status = billing.get_license_status()
    totals = billing.lifetime_totals()
    period = _period_now()
    items = billing.list_ledger(period)
    rollup = (
        rollup_period(items)
        if items
        else {"gross_profit_usd": 0, "license_fee_usd": 0, "net_benefit_usd": 0}
    )
    can_trade, gate_reason = check_license_gate(enrollment, status, dry_run=dry_run)
    milestones = detect_milestones(totals["lifetime_gross_profit_usd"], billing.list_milestones())
    preview_rate = float(enrollment.get("license_rate_pct", DEFAULT_LICENSE_RATE))
    return {
        "enrollment": enrollment,
        "license_status": status,
        "lifetime": totals,
        "current_period": period,
        "period_rollup": rollup,
        "line_items": items[:50],
        "statements": billing.list_statements(),
        "can_trade_live": can_trade,
        "license_gate_reason": gate_reason,
        "net_loss_equals_zero_fee": True,
        "milestones_pending": milestones,
        "dry_run_fee_preview": {
            "rate_pct": preview_rate,
            "sample_profit_usd": 100,
            "sample_fee_usd": round(100 * preview_rate, 2),
        },
        "disclaimer": "Software license only. User initiates payment externally.",
        "payment_auto_verify": True,
        "grace_period_days": GRACE_PERIOD_DAYS,
        "payment_assets": list_available_assets(),
        "billing_eligibility": eligibility_snapshot(enrollment),
    }


def start_settlement_payment(
    billing: BillingStore,
    *,
    period: str,
    amount_usd: float,
    asset: str = "BTC",
) -> dict[str, Any]:
    install_uuid = billing.get_or_create_install_uuid()
    asset_key = asset.strip().upper()
    existing = billing.get_active_payment_for_period(period, install_uuid, asset=asset_key)
    if existing:
        return enrich_payment_response(existing)
    return create_payment_intent(
        billing,
        period=period,
        amount_usd=amount_usd,
        install_uuid=install_uuid,
        asset_id=asset_key,
    )


def check_settlement_payment(
    billing: BillingStore,
    payment_id: str,
    *,
    simulate_tx_hash: str | None = None,
) -> dict[str, Any]:
    return verify_pending_payment(billing, payment_id, simulate_tx_hash=simulate_tx_hash)


def poll_settlement_payments(billing: BillingStore) -> dict[str, Any]:
    return watch_pending_payments(billing)


def reconcile_fees(billing: BillingStore, journal: TradeJournal) -> dict[str, Any]:
    ledger_refs = {e["trade_ref"] for e in billing.list_ledger(limit=ALL_TRADES)}
    journal_refs = {t["exchange_trade_id"] for t in journal.list_trades(limit=ALL_TRADES)}
    missing_in_ledger = sorted(journal_refs - ledger_refs)
    orphan_ledger = sorted(ledger_refs - journal_refs)
    ok = not missing_in_ledger and not orphan_ledger
    return {
        "ok": ok,
        "journal_count": len(journal_refs),
        "ledger_count": len(ledger_refs),
        "missing_in_ledger": missing_in_ledger,
        "orphan_ledger": orphan_ledger,
    }


def mark_payment_received(billing: BillingStore) -> dict[str, Any]:
    status = billing.get_license_status()
    period = str(status.get("unpaid_period") or _period_now())
    cleared = clear_grace(status)
    cleared["licensed_until"] = licensed_until_for_period(period)
    billing.update_license_status(cleared)
    return billing.get_license_status()
