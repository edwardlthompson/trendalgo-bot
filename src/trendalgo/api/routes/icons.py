from typing import Any

from fastapi import APIRouter, HTTPException

from trendalgo.api.state import _data_dir
from trendalgo.icons.aliases import resolve_symbol
from trendalgo.icons.store import IconStore

router = APIRouter()


def _store() -> IconStore:
    return IconStore(_data_dir() / "icon-registry.db")


@router.get("/icons/exchanges")
def list_exchange_icons() -> dict[str, Any]:
    store = _store()
    return {"exchanges": store.list_exchanges()}


@router.get("/icons/coin/{symbol}")
def get_coin_icon(symbol: str) -> dict[str, Any]:
    store = _store()
    resolved = resolve_symbol(symbol)
    row = store.get_coin(resolved) or store.get_coin(symbol)
    if not row:
        raise HTTPException(status_code=404, detail=f"unknown coin symbol: {symbol}")
    return row


@router.get("/icons/stats")
def icon_stats() -> dict[str, Any]:
    store = _store()
    return {
        "exchange_count": len(store.list_exchanges()),
        "coin_count": store.coin_count(),
    }
