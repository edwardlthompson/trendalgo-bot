"""Performance license billing API (Sprint 10)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from trendalgo.billing.engine import (
    build_dashboard,
    mark_payment_received,
    process_journal_trades,
    reconcile_fees,
    seed_sample_trades,
)
from trendalgo.billing.lightning import create_lightning_invoice
from trendalgo.billing.settlement import settlement_info
from trendalgo.billing.statements import export_statement_json
from trendalgo.billing.schema import DEFAULT_LICENSE_RATE

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


@router.get("/billing/dashboard")
def billing_dashboard(request: Request) -> dict[str, Any]:
    state = request.app.state.trendalgo
    return build_dashboard(state.billing_store, state.risk_manager, dry_run=state.bot.dry_run)


@router.get("/billing/preview")
def billing_preview(request: Request) -> dict[str, Any]:
    state = request.app.state.trendalgo
    dash = build_dashboard(state.billing_store, state.risk_manager, dry_run=state.bot.dry_run)
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
def billing_settlement(request: Request, period: str | None = None) -> dict[str, Any]:
    state = request.app.state.trendalgo
    period = period or state.billing_store.list_statements()[0]["period"] if state.billing_store.list_statements() else "current"
    stmt = state.billing_store.get_statement(period)
    amount = float(stmt["license_fee_usd"]) if stmt else 0.0
    return settlement_info(amount, period)


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
    """User confirms external payment — clears grace (no custody)."""
    state = request.app.state.trendalgo
    status = mark_payment_received(state.billing_store)
    state.log("license marked paid by user")
    return {"status": status}


@router.get("/billing/reconcile")
def billing_reconcile(request: Request) -> dict[str, Any]:
    state = request.app.state.trendalgo
    return reconcile_fees(state.billing_store, state.trade_journal)
