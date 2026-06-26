"""Exchange registry API routes (S13)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

from trendalgo.exchanges.registry import load_registry, list_exchanges

router = APIRouter()


@router.get("/exchanges/registry")
def exchanges_registry(_request: Request) -> dict[str, Any]:
    registry = load_registry()
    return {
        "version": registry.version,
        "exchanges": [entry.to_public_dict() for entry in list_exchanges()],
    }
