"""Portfolio overview assembly for API + scheduler."""

from __future__ import annotations

from typing import Any

from trendalgo.api.state import AppState
from trendalgo.portfolio.benchmarks import benchmark_curves
from trendalgo.portfolio.comparisons import yoy_mom_comparison
from trendalgo.portfolio.drawdown import max_drawdown
from trendalgo.portfolio.goals import goal_progress
from trendalgo.portfolio.health import health_score
from trendalgo.portfolio.metrics import (
    allocation_rows,
    daily_pnl_from_curve,
    enrich_holdings,
    period_comparison,
    pl_breakdown,
)
from trendalgo.portfolio.multi_exchange import aggregate_holdings
from trendalgo.portfolio.performance import (
    PERFORMANCE_RANGES,
    build_performance_payload,
    curve_for_metrics,
    ensure_btc_dry_run_fixture,
    list_history_dates,
    performance_curve,
)
from trendalgo.portfolio.tags import tag_holdings


def build_portfolio_overview(state: AppState) -> dict[str, Any]:
    store = state.portfolio_store
    primary_id = store.get_or_create_account("kraken", "default")
    if state.bot.dry_run:
        ensure_btc_dry_run_fixture(store, primary_id)
    aggregated = aggregate_holdings(store)
    accounts = aggregated["accounts"]
    use_aggregated = len(accounts) >= 2

    if use_aggregated:
        net_worth = float(aggregated["total_usd"])
        raw_holdings = aggregated["holdings"]
        account_id = primary_id
    else:
        snap = store.latest_snapshot(primary_id)
        net_worth = float(snap["total_usd"]) if snap else 0.0
        raw_holdings = snap["holdings"] if snap else []
        account_id = primary_id

    curve = curve_for_metrics(performance_curve(store, primary_id, "1y"))
    daily_pnl_usd, daily_pnl_pct = daily_pnl_from_curve(curve)
    tag_map = store.get_asset_tags()
    holdings = enrich_holdings(tag_holdings(raw_holdings, tag_map))
    allocation = allocation_rows(raw_holdings, net_worth)
    pl = pl_breakdown(raw_holdings)
    dd = max_drawdown(curve)
    health = health_score(allocation, dd, daily_pnl_pct)
    perf_default = build_performance_payload(store, primary_id, "1y", dry_run=state.bot.dry_run)
    equity = perf_default["points"]  # type: ignore[assignment]
    top10_comparison = perf_default.get("comparison", {})
    top10_index = perf_default.get("top10_index", [])
    benchmarks = {
        "top10_index": top10_index,
        **benchmark_curves(curve),
    }
    periods = [p.__dict__ for p in period_comparison(curve)]
    daily_aggs = store.list_daily_aggregates(primary_id, limit=365)
    comparisons = yoy_mom_comparison(daily_aggs, curve)
    comparison_payload = perf_default.get("comparison", {})
    alpha_pct = float(comparison_payload.get("alpha_pct", 0)) / 100.0 if comparison_payload else 0.0
    goal = goal_progress(
        net_worth,
        store.get_performance_goal(),
        max_drawdown_pct=dd,
        comparisons=comparisons,
        alpha_pct=alpha_pct,
    )
    bot = {
        "dry_run": state.bot.dry_run,
        "equity_usd": state.bot.equity_usd,
        "open_trades": state.bot.open_trades,
        "open_orders": state.bot.open_orders,
        "strategy_id": state.bot.strategy_id,
        "pair": state.bot.pair,
    }
    snap = store.latest_snapshot(primary_id)
    return {
        "account_id": account_id,
        "net_worth_usd": net_worth,
        "daily_pnl_usd": daily_pnl_usd,
        "daily_pnl_pct": daily_pnl_pct,
        "holdings": holdings,
        "allocation": allocation,
        "pl_breakdown": pl.__dict__,
        "periods": periods,
        "comparisons": comparisons,
        "equity_curve": equity,
        "top10_comparison": top10_comparison,
        "performance_ranges": list(PERFORMANCE_RANGES.keys()),
        "performance_range_default": "1y",
        "benchmarks": benchmarks,
        "max_drawdown_pct": dd,
        "health_score": health,
        "snapshot_dates": list_history_dates(store, primary_id, limit=365),
        "daily_aggregates": store.list_daily_aggregates(primary_id, limit=30),
        "accounts": accounts,
        "exchange_count": len(accounts),
        "aggregated": use_aggregated,
        "performance_goal": goal,
        "bot": bot,
        "latest_snapshot": snap,
    }


def heatmap_rows(holdings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for h in holdings:
        pct = float(h.get("pct_change", 0))
        vol = abs(pct) * 100
        rows.append(
            {
                "asset": h["asset"],
                "return_pct": round(pct * 100, 2),
                "volatility_pct": round(vol, 2),
            }
        )
    return sorted(rows, key=lambda r: abs(r["return_pct"]), reverse=True)
