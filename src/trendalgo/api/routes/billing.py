"""Performance license billing API (Sprint 10)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from trendalgo.billing.engine import (
    build_dashboard,
    check_settlement_payment,
    mark_payment_received,
    poll_settlement_payments,
    process_journal_trades,
    reconcile_fees,
    seed_sample_trades,
    start_settlement_payment,
)
from trendalgo.billing.lightning import create_lightning_invoice
from trendalgo.billing.schema import DEFAULT_LICENSE_RATE
from trendalgo.billing.settlement import list_available_assets
from trendalgo.billing.statements import export_statement_json

router = APIRouter()


class EnrollBody(BaseModel):
    license_rate_pct: float = Field(DEFAULT_LICENSE_RATE, ge=0.05, le=0.25)
    terms_version: str
    accept_terms: bool = True

    model_config = {"extra": "forbid"}


class TermsBody(BaseModel):
    terms_version: str

    model_config = {"extra": "forbid"}


class LightningBody(BaseModel):
    period: str
    amount_usd: float = Field(..., gt=0)

    model_config = {"extra": "forbid"}


class PaymentStartBody(BaseModel):
    period: str | None = None
    asset: str = "BTC"

    model_config = {"extra": "forbid"}


class PaymentCheckBody(BaseModel):
    payment_id: str
    simulate_tx_hash: str | None = None

    model_config = {"extra": "forbid"}


def _resolve_period_and_amount(store: Any, period: str | None) -> tuple[str, float]:
    if period is None:
        statements = store.list_statements()
        status = store.get_license_status()
        period = str(status.get("unpaid_period") or (statements[0]["period"] if statements else ""))
    if not period or period == "current":
        from datetime import UTC, datetime

        period = datetime.now(UTC).strftime("%Y-%m")
    stmt = store.get_statement(period)
    amount = float(stmt["license_fee_usd"]) if stmt else 0.0
    return period, amount


@router.get("/billing/payment/assets")
def billing_payment_assets() -> dict[str, Any]:
    return {"assets": list_available_assets()}


@router.get("/billing/dashboard")
def billing_dashboard(request: Request) -> dict[str, Any]:
    state = request.app.state.trendalgo
    return build_dashboard(
        state.billing_store,
        state.risk_manager,
        journal=state.trade_journal,
        dry_run=state.bot.dry_run,
    )


@router.get("/billing/preview")
def billing_preview(request: Request) -> dict[str, Any]:
    state = request.app.state.trendalgo
    dash = build_dashboard(
        state.billing_store,
        state.risk_manager,
        journal=state.trade_journal,
        dry_run=state.bot.dry_run,
    )
    return {"preview": dash["dry_run_fee_preview"], "disclaimer": dash["disclaimer"]}


@router.get("/billing/license-status")
def billing_license_status(request: Request) -> dict[str, Any]:
    state = request.app.state.trendalgo
    return {
        "enrollment": state.billing_store.get_enrollment(),
        "status": state.billing_store.get_license_status(),
    }


@router.post("/billing/enroll")
def billing_enroll(body: EnrollBody, request: Request) -> dict[str, Any]:
    if not body.accept_terms:
        raise HTTPException(status_code=400, detail="terms must be accepted")
    state = request.app.state.trendalgo
    install_uuid = state.billing_store.get_or_create_install_uuid()
    state.billing_store.log_terms_acceptance(body.terms_version, install_uuid)
    enrolled = state.billing_store.enroll(body.license_rate_pct, body.terms_version, install_uuid)
    state.log(f"performance license enrolled at {body.license_rate_pct:.0%}")
    return {"enrollment": enrolled, "install_uuid": install_uuid}


@router.post("/billing/terms/accept")
def billing_terms_accept(body: TermsBody, request: Request) -> dict[str, Any]:
    state = request.app.state.trendalgo
    install_uuid = state.billing_store.get_or_create_install_uuid()
    log_id = state.billing_store.log_terms_acceptance(body.terms_version, install_uuid)
    return {"id": log_id, "install_uuid": install_uuid, "terms_version": body.terms_version}


@router.get("/billing/statement/{period}")
def billing_statement(period: str, request: Request) -> dict[str, Any]:
    stmt = request.app.state.trendalgo.billing_store.get_statement(period)
    if stmt is None:
        raise HTTPException(status_code=404, detail="statement not found")
    return stmt


@router.get("/billing/statement/{period}/export")
def billing_statement_export(period: str, request: Request) -> PlainTextResponse:
    stmt = request.app.state.trendalgo.billing_store.get_statement(period)
    if stmt is None:
        raise HTTPException(status_code=404, detail="statement not found")
    return PlainTextResponse(export_statement_json(stmt), media_type="application/json")


@router.get("/billing/settlement")
def billing_settlement(
    request: Request,
    period: str | None = None,
    asset: str = "BTC",
) -> dict[str, Any]:
    state = request.app.state.trendalgo
    resolved, amount = _resolve_period_and_amount(state.billing_store, period)
    return start_settlement_payment(
        state.billing_store, period=resolved, amount_usd=amount, asset=asset
    )


@router.post("/billing/payment/start")
def billing_payment_start(body: PaymentStartBody, request: Request) -> dict[str, Any]:
    state = request.app.state.trendalgo
    resolved, amount = _resolve_period_and_amount(state.billing_store, body.period)
    if amount <= 0:
        raise HTTPException(status_code=400, detail="no license fee due for this period")
    return start_settlement_payment(
        state.billing_store,
        period=resolved,
        amount_usd=amount,
        asset=body.asset,
    )


@router.get("/billing/payment/status/{payment_id}")
def billing_payment_status(payment_id: str, request: Request) -> dict[str, Any]:
    state = request.app.state.trendalgo
    try:
        return check_settlement_payment(state.billing_store, payment_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/billing/payment/check")
def billing_payment_check(body: PaymentCheckBody, request: Request) -> dict[str, Any]:
    state = request.app.state.trendalgo
    try:
        return check_settlement_payment(
            state.billing_store,
            body.payment_id,
            simulate_tx_hash=body.simulate_tx_hash,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/billing/payment/watch")
def billing_payment_watch(request: Request) -> dict[str, Any]:
    state = request.app.state.trendalgo
    return poll_settlement_payments(state.billing_store)


@router.post("/billing/lightning-invoice")
def billing_lightning(body: LightningBody, request: Request) -> dict[str, Any]:
    return create_lightning_invoice(body.amount_usd, body.period)


@router.post("/billing/process-trades")
def billing_process_trades(request: Request) -> dict[str, Any]:
    state = request.app.state.trendalgo
    seed_sample_trades(state.trade_journal)
    return process_journal_trades(state.billing_store, state.trade_journal, state.risk_manager)


@router.post("/billing/mark-paid")
def billing_mark_paid(request: Request) -> dict[str, Any]:
    """Fallback when on-chain auto-verify is unavailable."""
    state = request.app.state.trendalgo
    status = mark_payment_received(state.billing_store)
    state.log("license marked paid by user")
    return {"status": status}


@router.get("/billing/reconcile")
def billing_reconcile(request: Request) -> dict[str, Any]:
    state = request.app.state.trendalgo
    return reconcile_fees(state.billing_store, state.trade_journal)
