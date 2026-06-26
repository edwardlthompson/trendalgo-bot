"""AI strategy routes (Sprint 11)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from trendalgo.ai.curated_library import list_curated
from trendalgo.ai.nl_draft import draft_from_nl
from trendalgo.ai.recommender import recommend_strategies
from trendalgo.ai.scanner_pipeline import pipeline_suggestions
from trendalgo.api.risk import get_risk_status
from trendalgo.billing.boost import disable_boost_mode, enable_boost_mode
from trendalgo.growth.store import GrowthStore

router = APIRouter()


class NlDraftBody(BaseModel):
    text: str = Field(..., min_length=3, max_length=2000)

    model_config = {"extra": "forbid"}


class LeaderboardBody(BaseModel):
    score_usd: float = Field(..., ge=0)

    model_config = {"extra": "forbid"}


def _growth_store(request: Request) -> GrowthStore:
    return request.app.state.trendalgo.growth_store


def _install_uuid(state: Any) -> str:
    return state.billing_store.get_or_create_install_uuid()


@router.get("/ai/recommendations")
def ai_recommendations(request: Request) -> dict[str, Any]:
    state = request.app.state.trendalgo
    snap = state.scanner_store.latest_snapshot()
    opps = [o.model_dump() for o in snap.opportunities] if snap else []
    top_u = max((float(o.get("uniformity", 0)) for o in opps), default=0.0)
    risk = get_risk_status(state.risk_manager)
    recs = recommend_strategies(opps, risk, top_scanner_uniformity=top_u)
    return {
        "recommendations": recs,
        "risk_profile": risk,
        "disclaimer": "AI suggestions require backtest and param confirmation. Not financial advice.",
    }


@router.get("/ai/scanner-pipeline")
def ai_scanner_pipeline(request: Request) -> dict[str, Any]:
    state = request.app.state.trendalgo
    snap = state.scanner_store.latest_snapshot()
    opps = [o.model_dump() for o in snap.opportunities] if snap else []
    return {"suggestions": pipeline_suggestions(opps)}


@router.get("/ai/curated-library")
def ai_curated_library() -> dict[str, Any]:
    return list_curated()


@router.post("/ai/nl-draft")
def ai_nl_draft(body: NlDraftBody, request: Request) -> dict[str, Any]:
    draft = draft_from_nl(body.text)
    request.app.state.trendalgo.log("nl strategy draft generated")
    return draft


@router.get("/growth/referral")
def growth_referral(request: Request) -> dict[str, Any]:
    state = request.app.state.trendalgo
    uuid = _install_uuid(state)
    return _growth_store(request).get_or_create_referral(uuid)


@router.post("/growth/leaderboard/opt-in")
def growth_leaderboard_opt_in(body: LeaderboardBody, request: Request) -> dict[str, Any]:
    state = request.app.state.trendalgo
    uuid = _install_uuid(state)
    return _growth_store(request).opt_in_leaderboard(uuid, body.score_usd)


@router.post("/growth/leaderboard/opt-out")
def growth_leaderboard_opt_out(request: Request) -> dict[str, str]:
    state = request.app.state.trendalgo
    uuid = _install_uuid(state)
    _growth_store(request).opt_out_leaderboard(uuid)
    return {"ok": True}


@router.get("/growth/leaderboard")
def growth_leaderboard(request: Request) -> dict[str, Any]:
    rows = _growth_store(request).leaderboard_rows()
    return {"rows": rows, "no_pii": True, "opt_in_only": True}


@router.post("/billing/boost-mode")
def billing_boost_enable(request: Request) -> dict[str, Any]:
    return enable_boost_mode(request.app.state.trendalgo.billing_store)


@router.post("/billing/boost-mode/disable")
def billing_boost_disable(request: Request) -> dict[str, Any]:
    return disable_boost_mode(request.app.state.trendalgo.billing_store)
