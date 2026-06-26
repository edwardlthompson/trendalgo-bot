"""Platform extension routes — Sprint 12."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from trendalgo.billing.onchain_receipts import issue_fee_receipt, verify_fee_receipt
from trendalgo.data.onchain_sentiment import onchain_sentiment_stub
from trendalgo.db.postgres_adapter import PostgresDualWrite
from trendalgo.dex.load_test import run_dex_ops_validation
from trendalgo.dex.router import (
    dex_trading_status,
    dry_run_dex_swap,
    list_dex_swap_chains,
    live_dex_swap,
    preview_dex_swap,
)
from trendalgo.dex.rpc import rpc_status
from trendalgo.portfolio.onchain import preview_onchain_wallet, sync_onchain_wallet
from trendalgo.scanner.forager import forage_pairs
from trendalgo.trading.funding import fetch_funding_rates, funding_profit_estimate
from trendalgo.trading.multi_exchange import list_supported_exchanges, route_order
from trendalgo.venues.orchestrator import sync_all_wallet_venues
from trendalgo.venues.plugins.zero_ex import preview_quote
from trendalgo.venues.registry import (
    get_venue,
    list_wallet_venues,
    load_venue_registry,
    venue_public_dict,
)

router = APIRouter(prefix="/platform")


class DexSwapBody(BaseModel):
    chain: str = "ethereum"
    sell_token: str = Field(..., min_length=1, max_length=16)
    buy_token: str = Field(..., min_length=1, max_length=16)
    sell_amount: float = Field(..., gt=0)
    slippage_bps: int = Field(50, ge=0, le=500)

    model_config = {"extra": "forbid"}


class OnchainSyncBody(BaseModel):
    address: str = Field(..., min_length=10, max_length=64)
    chain: str = "ethereum"
    include_lp: bool = True

    model_config = {"extra": "forbid"}


class OnchainSyncAllBody(BaseModel):
    address: str = Field(..., min_length=10, max_length=64)
    include_lp: bool = True

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


@router.get("/venues/registry")
def venues_registry() -> dict[str, Any]:
    registry = load_venue_registry()
    return {
        "version": registry.version,
        "venues": [venue_public_dict(v) for v in list_wallet_venues()],
    }


@router.get("/onchain/preview/{address}")
def onchain_preview(
    address: str, chain: str = "ethereum", include_lp: bool = True
) -> dict[str, Any]:
    try:
        return preview_onchain_wallet(address, chain=chain, include_lp=include_lp)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/onchain/sync")
def onchain_sync(request: Request, body: OnchainSyncBody) -> dict[str, Any]:
    state = request.app.state.trendalgo
    try:
        return sync_onchain_wallet(
            state.portfolio_store,
            body.address,
            chain=body.chain,
            dry_run=state.bot.dry_run,
            include_lp=body.include_lp,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/onchain/sync-all")
def onchain_sync_all(request: Request, body: OnchainSyncAllBody) -> dict[str, Any]:
    state = request.app.state.trendalgo
    try:
        return sync_all_wallet_venues(
            state.portfolio_store,
            body.address,
            dry_run=state.bot.dry_run,
            include_lp=body.include_lp,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/dex/swap-chains")
def dex_swap_chains() -> dict[str, Any]:
    return {
        "chains": list_dex_swap_chains(),
        "live_trading_venues": dex_trading_status()["live_trading_venues"],
    }


@router.get("/dex/status")
def dex_status_route() -> dict[str, Any]:
    state = dex_trading_status()
    state["control"] = []
    return state


@router.get("/dex/status/full")
def dex_status_full(request: Request) -> dict[str, Any]:
    status = dex_trading_status()
    status["control"] = request.app.state.trendalgo.dex_control.list_status()
    status["nonces"] = request.app.state.trendalgo.dex_nonce_store.status()
    rpc_rows = []
    for entry in list_wallet_venues():
        if entry.swap_plugins:
            rpc_rows.append(rpc_status(entry))
    status["rpc"] = rpc_rows
    return status


@router.post("/dex/venues/{venue_id}/go-live")
def dex_venue_go_live(venue_id: str, request: Request) -> dict[str, Any]:
    try:
        get_venue(venue_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    request.app.state.trendalgo.dex_control.approve_go_live(venue_id)
    return {"venue_id": venue_id, "go_live_approved": True}


@router.get("/dex/ops-validation")
def dex_ops_validation() -> dict[str, Any]:
    return run_dex_ops_validation()


@router.get("/dex/preview")
def dex_swap_preview(
    chain: str = "ethereum",
    sell_token: str = "ETH",
    buy_token: str = "USDC",
    sell_amount: float = 1.0,
) -> dict[str, Any]:
    try:
        return preview_dex_swap(chain, sell_token, buy_token, sell_amount)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/dex/dry-run")
def dex_swap_dry_run(request: Request, body: DexSwapBody) -> dict[str, Any]:
    state = request.app.state.trendalgo
    try:
        return dry_run_dex_swap(
            body.chain,
            body.sell_token,
            body.buy_token,
            body.sell_amount,
            app_dry_run=state.bot.dry_run,
            live_swap=False,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/dex/live")
def dex_swap_live(request: Request, body: DexSwapBody) -> dict[str, Any]:
    state = request.app.state.trendalgo
    try:
        return live_dex_swap(
            body.chain,
            body.sell_token,
            body.buy_token,
            body.sell_amount,
            control=state.dex_control,
            nonce_store=state.dex_nonce_store,
            slippage_bps=body.slippage_bps,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/dex/quote")
def dex_quote_preview(
    request: Request,
    chain: str = "ethereum",
    sell_token: str = "ETH",
    buy_token: str = "USDC",
    sell_amount: float = 1.0,
) -> dict[str, Any]:
    state = request.app.state.trendalgo
    try:
        return preview_quote(
            chain,
            sell_token,
            buy_token,
            sell_amount,
            dry_run=state.bot.dry_run,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/forager")
def forager_pairs_route() -> dict[str, Any]:
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
