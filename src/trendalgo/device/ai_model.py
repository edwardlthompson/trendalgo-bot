"""Device AI panel: curated presets and rule-based recommendations (FOSS, no cloud LLM)."""

from __future__ import annotations

from typing import Any

from trendalgo.ai.curated_library import list_curated
from trendalgo.ai.recommender import recommend_strategies
from trendalgo.device.portfolio_model import load_overview
from trendalgo.device.stores import StoreReadError
from trendalgo.scanner.snapshot import OpportunityRow
from trendalgo.scanner.store import ScannerStore


def curated_library() -> dict[str, Any]:
    return list_curated()


def _risk_from_equity(equity_usd: float) -> dict[str, Any]:
    return {
        "equity_usd": equity_usd,
        "drawdown_pct": 0.0,
        "circuit_breaker_active": False,
    }


def _opportunity_dict(row: OpportunityRow) -> dict[str, Any]:
    return {
        "rank": row.rank,
        "pair": row.pair,
        "uniformity": row.uniformity,
        "gain_pct": row.gain_pct,
        "volume_score": row.volume_score,
        "entry_signal": row.entry_signal,
    }


def load_scanner_opportunities(scanner_db: Any) -> tuple[list[dict[str, Any]], float]:
    try:
        snap = ScannerStore(scanner_db).latest_snapshot()
    except StoreReadError:
        return [], 0.0
    if snap is None:
        return [], 0.0
    opps = [_opportunity_dict(row) for row in snap.opportunities]
    top_u = max((float(o.get("uniformity", 0)) for o in opps), default=0.0)
    return opps, top_u


def device_recommendations(
    *,
    scanner_db: Any,
    portfolio_db: Any | None,
) -> dict[str, Any]:
    opps, top_u = load_scanner_opportunities(scanner_db)
    equity = 0.0
    if portfolio_db is not None:
        try:
            overview = load_overview(portfolio_db)
            if overview is not None:
                equity = float(overview.net_worth_usd)
        except StoreReadError:
            equity = 0.0
    risk = _risk_from_equity(equity)
    recs = recommend_strategies(opps, risk, top_scanner_uniformity=top_u)
    return {
        "recommendations": recs,
        "has_scanner_data": bool(opps),
        "risk_profile": risk,
        "disclaimer": (
            "Suggestions rank bundled strategy templates from your latest scan and a simple "
            "risk profile. Backtest every idea and confirm parameters before you add bots."
        ),
    }
