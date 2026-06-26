from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

router = APIRouter()


class WatchlistBody(BaseModel):
    pair: str = Field(..., min_length=3)
    alert_price_pct: float = Field(0.05, ge=0.01, le=0.5)
    alert_pl_usd: float = Field(50, ge=1)

    model_config = {"extra": "forbid"}


@router.get("/watchlist")
def get_watchlist(request: Request) -> dict[str, Any]:
    items = request.app.state.trendalgo.watchlist_store.list_items()
    return {"items": items}


@router.post("/watchlist")
def add_watchlist(body: WatchlistBody, request: Request) -> dict[str, Any]:
    store = request.app.state.trendalgo.watchlist_store
    store.add(body.pair, body.alert_price_pct, body.alert_pl_usd)
    request.app.state.trendalgo.log(f"watchlist add: {body.pair}")
    return {"items": store.list_items()}


@router.post("/watchlist/check")
def check_watchlist_alerts(request: Request) -> dict[str, Any]:
    store = request.app.state.trendalgo.watchlist_store
    fired: list[str] = []
    for item in store.list_items():
        msg = store.check_price_move(item["pair"], 0.06)
        if msg:
            fired.append(msg)
            request.app.state.trendalgo.portfolio_store.insert_notification(
                "watchlist", "Price alert", msg
            )
    return {"alerts": fired}
