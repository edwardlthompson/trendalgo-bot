from typing import Any

from fastapi import APIRouter, Request

from trendalgo.notifications.grokbot import public_status, send_test
from trendalgo.notifications.preferences import (
    NotificationPreferences,
    load_preferences,
    save_preferences,
)

router = APIRouter()


@router.get("/notifications/preferences")
def get_prefs(request: Request) -> dict[str, object]:
    store = request.app.state.trendalgo.portfolio_store
    prefs = load_preferences(store)
    return prefs.model_dump()


@router.put("/notifications/preferences")
def put_prefs(body: NotificationPreferences, request: Request) -> dict[str, object]:
    store = request.app.state.trendalgo.portfolio_store
    saved = save_preferences(store, body)
    request.app.state.trendalgo.log("notification preferences updated")
    return saved.model_dump()


@router.get("/notifications/inbox")
def notification_inbox(request: Request) -> dict[str, object]:
    store = request.app.state.trendalgo.portfolio_store
    return {"items": store.list_notifications()}


@router.get("/notifications/grokbot")
def grokbot_status() -> dict[str, Any]:
    return public_status()


@router.post("/notifications/grokbot/test")
def grokbot_test(request: Request) -> dict[str, Any]:
    result = send_test(wait=True)
    request.app.state.trendalgo.log(f"grokbot test: sent={result.get('sent')}")
    return result
