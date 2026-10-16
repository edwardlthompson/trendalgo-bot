"""Research panel helpers: correlation note export from local portfolio holdings."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from trendalgo.device.portfolio_model import PortfolioOverview, load_overview
from trendalgo.device.stores import StoreReadError
from trendalgo.portfolio.correlation import correlation_matrix, diversification_suggestions

CORRELATION_JSON_NAME = "correlation-note.json"


def load_portfolio_overview(path: Path | None) -> PortfolioOverview | None:
    if path is None:
        return None
    try:
        return load_overview(path)
    except StoreReadError:
        return None


def correlation_note_payload(overview: PortfolioOverview | None) -> dict[str, Any] | None:
    if overview is None:
        return None
    positive = [h for h in overview.holdings if float(h.get("value_usd", 0)) > 0]
    if len(positive) < 2:
        return None
    allocation = sorted(positive, key=lambda h: float(h.get("value_usd", 0)), reverse=True)
    matrix = correlation_matrix(allocation)
    tips = diversification_suggestions(allocation)
    return {
        "captured_at": overview.captured_at,
        "source": overview.source,
        "correlation": matrix,
        "suggestions": tips,
        "disclaimer": (
            "Placeholder pairwise values on this device. Live research runs on the host API, "
            "not in this app yet."
        ),
    }


def write_correlation_note(dest_dir: Path, payload: dict[str, Any]) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    path = dest_dir / CORRELATION_JSON_NAME
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path
