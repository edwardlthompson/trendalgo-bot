"""Hyperopt trigger stub (T30) — native optimize path in S17."""

from __future__ import annotations

from typing import Any


def trigger_hyperopt(strategy: str, pair: str, epochs: int = 50) -> dict[str, Any]:
    return {
        "status": "queued",
        "strategy": strategy,
        "pair": pair,
        "epochs": epochs,
        "message": "Hyperopt job queued (native stub — walk-forward in optimize/)",
    }
