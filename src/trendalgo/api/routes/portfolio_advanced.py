"""Portfolio advanced routes — Sprint 8."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from trendalgo.api.public_dashboard import public_overview_payload
from trendalgo.notifications.discord import send_discord_message
from trendalgo.notifications.email import send_smtp_email
from trendalgo.portfolio.arbitrage import detect_arbitrage_opportunities
from trendalgo.portfolio.basket import apply_basket_to_bots, normalize_weights
from trendalgo.portfolio.dex_positions import list_dex_positions_from_store, preview_dex_positions
from trendalgo.portfolio.goals import goal_progress
from trendalgo.portfolio.multi_exchange import aggregate_holdings, sync_all_exchanges
from trendalgo.portfolio.overview import build_portfolio_overview
from trendalgo.portfolio.rebalance import rebalance_suggestions
from trendalgo.portfolio.tags import default_tag

router = APIRouter()


class TagBody(BaseModel):
    tag: str = Field(..., min_length=1, max_length=32)

    model_config = {"extra": "forbid"}


class CostBasisBody(BaseModel):
    cost_basis_usd: float = Field(..., ge=0)

    model_config = {"extra": "forbid"}


class TargetBody(BaseModel):
    asset: str
    target_pct: float = Field(..., ge=0, le=1)

    model_config = {"extra": "forbid"}


class GoalBody(BaseModel):
    target_net_worth_usd: float = Field(..., gt=0)
    label: str = "Growth goal"
    deadline: str | None = None
    goal_type: str = "portfolio_growth"
    horizon_months: int = Field(default=12, ge=1, le=120)
    target_return_pct: float = Field(default=0.0, ge=0, le=100)

    model_config = {"extra": "forbid"}


class BasketBody(BaseModel):
    weights: dict[str, float] = Field(default_factory=dict)

    model_config = {"extra": "forbid"}


class NotifyTestBody(BaseModel):
    message: str = "TrendAlgo test notification"

    model_config = {"extra": "forbid"}


@router.get("/portfolio/accounts")
def portfolio_accounts(request: Request) -> dict[str, Any]:
    store = request.app.state.trendalgo.portfolio_store
    return {"accounts": aggregate_holdings(store)["accounts"]}


@router.get("/portfolio/dex/positions")
def portfolio_dex_positions(
    request: Request,
    address: str | None = None,
    chain: str | None = None,
) -> dict[str, Any]:
    store = request.app.state.trendalgo.portfolio_store
    if address:
        try:
            return preview_dex_positions(address, chain=chain)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    return list_dex_positions_from_store(store)


@router.post("/portfolio/sync-all")
def portfolio_sync_all(request: Request) -> dict[str, Any]:
    state = request.app.state.trendalgo
    result = sync_all_exchanges(state.portfolio_store, dry_run=state.bot.dry_run)
    state.log("portfolio sync-all completed")
    return result


@router.get("/portfolio/tags")
def portfolio_tags(request: Request) -> dict[str, Any]:
    store = request.app.state.trendalgo.portfolio_store
    tags = store.get_asset_tags()
    overview = build_portfolio_overview(request.app.state.trendalgo)
    tagged = []
    for h in overview["holdings"]:
        asset = str(h["asset"])
        tagged.append(
            {"asset": asset, "tag": h.get("tag") or tags.get(asset) or default_tag(asset)}
        )
    return {"tags": tags, "holdings": tagged}


@router.put("/portfolio/tags/{asset}")
def portfolio_set_tag(asset: str, body: TagBody, request: Request) -> dict[str, Any]:
    store = request.app.state.trendalgo.portfolio_store
    store.set_asset_tag(asset, body.tag)
    return {"asset": asset, "tag": body.tag}


@router.put("/portfolio/cost-basis/{asset}")
def portfolio_cost_basis(asset: str, body: CostBasisBody, request: Request) -> dict[str, Any]:
    store = request.app.state.trendalgo.portfolio_store
    account_id = store.get_or_create_account("kraken", "default")
    store.set_manual_cost_basis(account_id, asset, body.cost_basis_usd)
    return {"asset": asset, "cost_basis_usd": body.cost_basis_usd}


@router.get("/portfolio/rebalance")
def portfolio_rebalance(request: Request) -> dict[str, Any]:
    state = request.app.state.trendalgo
    overview = build_portfolio_overview(state)
    account_id = int(overview["account_id"])
    targets = state.portfolio_store.list_allocation_targets(account_id)
    suggestions = rebalance_suggestions(
        overview["allocation"],
        targets,
        float(overview["net_worth_usd"]),
    )
    return {
        "targets": targets,
        "suggestions": suggestions,
        "manual_only": True,
        "disclaimer": "Suggestions only — apply trades manually on your exchange.",
    }


@router.post("/portfolio/rebalance/apply")
def portfolio_rebalance_apply(request: Request) -> dict[str, Any]:
    state = request.app.state.trendalgo
    overview = build_portfolio_overview(state)
    account_id = int(overview["account_id"])
    targets = state.portfolio_store.list_allocation_targets(account_id)
    suggestions = rebalance_suggestions(
        overview["allocation"],
        targets,
        float(overview["net_worth_usd"]),
    )
    if suggestions:
        top = suggestions[0]
        state.portfolio_store.insert_notification(
            "rebalance",
            "Rebalance reminder",
            f"Manual apply: {top['action']} ${abs(top['delta_usd'])} of {top['asset']}",
        )
    state.log("rebalance apply logged (manual only)")
    return {"logged": True, "suggestion_count": len(suggestions)}


@router.put("/portfolio/targets")
def portfolio_set_target(body: TargetBody, request: Request) -> dict[str, Any]:
    store = request.app.state.trendalgo.portfolio_store
    account_id = store.get_or_create_account("kraken", "default")
    store.set_allocation_target(account_id, body.asset, body.target_pct)
    return {"asset": body.asset, "target_pct": body.target_pct}


@router.get("/portfolio/arbitrage")
def portfolio_arbitrage(request: Request) -> dict[str, Any]:
    state = request.app.state.trendalgo
    return detect_arbitrage_opportunities(dry_run=state.bot.dry_run)


def _goal_from_overview(overview: dict[str, Any], goal_row: dict[str, Any]) -> dict[str, Any]:
    comparison = overview.get("top10_comparison") or {}
    alpha = float(comparison.get("alpha_pct", 0)) / 100.0
    return goal_progress(
        float(overview["net_worth_usd"]),
        goal_row,
        max_drawdown_pct=float(overview.get("max_drawdown_pct", 0)),
        comparisons=list(overview.get("comparisons") or []),
        alpha_pct=alpha,
    )


@router.get("/portfolio/goals")
def portfolio_goals(request: Request) -> dict[str, Any]:
    state = request.app.state.trendalgo
    overview = build_portfolio_overview(state)
    goal = _goal_from_overview(overview, state.portfolio_store.get_performance_goal())
    return {"goal": goal}


@router.put("/portfolio/goals")
def portfolio_put_goals(body: GoalBody, request: Request) -> dict[str, Any]:
    store = request.app.state.trendalgo.portfolio_store
    saved = store.update_performance_goal(
        body.target_net_worth_usd,
        body.label,
        body.deadline,
        goal_type=body.goal_type,
        horizon_months=body.horizon_months,
        target_return_pct=body.target_return_pct,
    )
    overview = build_portfolio_overview(request.app.state.trendalgo)
    return {"goal": _goal_from_overview(overview, saved)}


@router.get("/portfolio/basket")
def portfolio_basket(request: Request) -> dict[str, Any]:
    state = request.app.state.trendalgo
    weights = state.portfolio_store.get_basket_weights()
    overview = build_portfolio_overview(state)
    bots = state.bot_orchestrator.list_bots()
    applied = apply_basket_to_bots(bots, weights, float(overview["net_worth_usd"]))
    return {"weights": weights, "bots": applied}


@router.put("/portfolio/basket")
def portfolio_put_basket(body: BasketBody, request: Request) -> dict[str, Any]:
    state = request.app.state.trendalgo
    normalized = normalize_weights(body.weights)
    saved = state.portfolio_store.set_basket_weights(normalized)
    overview = build_portfolio_overview(state)
    bots = state.bot_orchestrator.list_bots()
    applied = apply_basket_to_bots(bots, saved, float(overview["net_worth_usd"]))
    return {"weights": saved, "bots": applied}


@router.post("/portfolio/public-share")
def portfolio_public_share(request: Request) -> dict[str, Any]:
    token = request.app.state.trendalgo.public_dashboard_store.create_token()
    return {"token": token, "url": f"/api/v1/public/dashboard/{token}"}


@router.get("/public/dashboard/{token}")
def public_dashboard(token: str, request: Request) -> dict[str, Any]:
    store = request.app.state.trendalgo.public_dashboard_store
    if not store.is_valid(token):
        raise HTTPException(status_code=404, detail="invalid or expired token")
    overview = build_portfolio_overview(request.app.state.trendalgo)
    return public_overview_payload(overview)


@router.post("/notifications/discord/test")
def discord_test(body: NotifyTestBody, request: Request) -> dict[str, Any]:
    result = send_discord_message(body.message)
    request.app.state.trendalgo.log(f"discord test: sent={result.get('sent')}")
    return result


@router.post("/notifications/email/test")
def email_test(body: NotifyTestBody, request: Request) -> dict[str, Any]:
    result = send_smtp_email("TrendAlgo test", body.message)
    request.app.state.trendalgo.log(f"email test: sent={result.get('sent')}")
    return result
