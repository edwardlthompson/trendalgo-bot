"""Export everything hub (T20)."""

from __future__ import annotations

import json
from typing import Any

from trendalgo.export.tax import tax_csv


def export_hub_manifest(state: Any) -> dict[str, Any]:
    """Build download manifest for portfolio, trades, settings, tax."""
    portfolio_store = state.portfolio_store
    account_id = portfolio_store.get_or_create_account("kraken", "default")
    trades: list[dict[str, Any]] = []
    if state.last_backtest and state.last_backtest.get("result"):
        trades = state.last_backtest["result"].get("trades", [])
    return {
        "exports": [
            {"id": "portfolio_csv", "path": "/api/v1/portfolio/export", "format": "csv"},
            {"id": "tax_csv", "path": "/api/v1/export/tax", "format": "csv"},
            {"id": "settings_json", "path": "/api/v1/export/settings", "format": "json"},
            {"id": "bundle_json", "path": "/api/v1/export/bundle", "format": "json"},
        ],
        "account_id": account_id,
        "trade_count": len(trades),
    }


def export_bundle(state: Any) -> dict[str, Any]:
    snap = state.portfolio_store.latest_snapshot(
        state.portfolio_store.get_or_create_account("kraken", "default")
    )
    trades: list[dict[str, Any]] = []
    if state.last_backtest and state.last_backtest.get("result"):
        trades = state.last_backtest["result"].get("trades", [])
    return {
        "portfolio": snap,
        "strategy_params": state.strategy_params,
        "last_backtest": state.last_backtest,
        "tax_csv_preview": tax_csv(trades).splitlines()[:5],
        "disclaimer": "Not tax advice. Verify with a qualified professional.",
    }


def export_settings_json(state: Any) -> dict[str, Any]:
    return {
        "strategy_params": state.strategy_params,
        "exit_rules": state.exit_rules,
        "dry_run": state.bot.dry_run,
    }
