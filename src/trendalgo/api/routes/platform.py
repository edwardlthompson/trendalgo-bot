"""Platform extension routes — Sprint 12."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from trendalgo.billing.onchain_receipts import issue_fee_receipt, verify_fee_receipt
from trendalgo.data.onchain_sentiment import onchain_sentiment_stub
from trendalgo.db.postgres_adapter import PostgresDualWrite
from trendalgo.portfolio.onchain import preview_onchain_wallet, sync_onchain_wallet
from trendalgo.scanner.forager import forage_pairs
from trendalgo.trading.funding import fetch_funding_rates, funding_profit_estimate
from trendalgo.trading.multi_exchange import list_supported_exchanges, route_order

router = APIRouter(prefix="/platform")


class OnchainSyncBody(BaseModel):
    address: str = Field(..., min_length=10, max_length=64)
    chain: str = "ethereum"

    model_config = {"extra": "forbid"}


class TradeRouteBody(BaseModel):
    exchange: str
    pair: str
    side: str
    amount: float = Field(..., gt=0)

    model_config = {"extra": "forbid"}


class FundingEstimateBody(BaseModel):
    position_usd: float = Field(..., ge=0)
    funding_rate_pct: float
    hours: int = Field(8, ge=1, le=24)

    model_config = {"extra": "forbid"}


class ReceiptVerifyBody(BaseModel):
    receipt_id: str
    tx_hash: str
    expected_hash: str

    model_config = {"extra": "forbid"}


@router.get("/onchain/preview/{address}")
def onchain_preview(address: str, chain: str = "ethereum") -> dict[str, Any]:
    try:
        return preview_onchain_wallet(address, chain=chain)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/onchain/sync")
def onchain_sync(request: Request, body: OnchainSyncBody) -> dict[str, Any]:
    state = request.app.state.trendalgo
    try:
        return sync_onchain_wallet(
            state.portfolio_store,
            body.address,
            chain=body.chain,
            dry_run=state.bot.dry_run,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/forager")
def forager_pairs() -> dict[str, Any]:
    return forage_pairs()


@router.get("/funding")
def funding_rates(exchange: str | None = None) -> dict[str, Any]:
    return fetch_funding_rates(exchange)


@router.post("/funding/estimate")
def funding_estimate(body: FundingEstimateBody) -> dict[str, Any]:
    try:
        return funding_profit_estimate(body.position_usd, body.funding_rate_pct, hours=body.hours)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/trading/exchanges")
def trading_exchanges() -> dict[str, Any]:
    return {"exchanges": list_supported_exchanges()}


@router.post("/trading/route")
def trading_route(request: Request, body: TradeRouteBody) -> dict[str, Any]:
    state = request.app.state.trendalgo
    try:
        return route_order(
            body.exchange,
            body.pair,
            body.side,
            body.amount,
            dry_run=state.bot.dry_run,
            control=state.exchange_control,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/fee-receipt/{period}")
def fee_receipt(period: str, amount_usd: float = 0, wallet: str | None = None) -> dict[str, Any]:
    return issue_fee_receipt(period, amount_usd, wallet=wallet)


@router.post("/fee-receipt/verify")
def fee_receipt_verify(body: ReceiptVerifyBody) -> dict[str, Any]:
    return verify_fee_receipt(body.receipt_id, body.tx_hash, body.expected_hash)


@router.get("/data/sentiment/{asset}")
def sentiment_stub(asset: str) -> dict[str, Any]:
    return onchain_sentiment_stub(asset)


@router.get("/postgres/status")
def postgres_status() -> dict[str, Any]:
    adapter = PostgresDualWrite()
    return adapter.status()


@router.post("/postgres/migrate-dry-run")
def postgres_migrate_dry_run() -> dict[str, Any]:
    adapter = PostgresDualWrite()
    return adapter.dry_run_migrate()
