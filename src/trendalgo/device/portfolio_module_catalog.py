"""Dashboard module catalog: ids, titles, default spans, factory page layouts."""

from __future__ import annotations

from dataclasses import dataclass, replace

from trendalgo.device import strings as S

CAT_OVERVIEW = "Overview"
CAT_ANALYTICS = "Analytics"
CAT_TRADING = "Trading"
CAT_MORE = "More"
CATEGORY_ORDER: tuple[str, ...] = (CAT_OVERVIEW, CAT_ANALYTICS, CAT_TRADING, CAT_MORE)


@dataclass(frozen=True)
class ModuleSpec:
    id: str
    title: str
    default_w: int = 12
    default_h: int = 4
    min_w: int = 4
    min_h: int = 2
    max_w: int = 24
    max_h: int = 16
    category: str = CAT_MORE


# 24-col square grid: horizontal spans are 2× the old 12-col catalog.
CATALOG: tuple[ModuleSpec, ...] = (
    ModuleSpec("total_worth", "Total Worth", 24, 4, 6, 5, category=CAT_OVERVIEW),
    ModuleSpec("pl_insights", "Profit Loss Insights", 24, 3, 6, 2, category=CAT_OVERVIEW),
    ModuleSpec("assets", "Assets", 14, 6, 8, 3, category=CAT_OVERVIEW),
    ModuleSpec("portfolio_value", "Portfolio Value", 16, 5, 8, 3, category=CAT_OVERVIEW),
    ModuleSpec("cumulative_pnl", "Cumulative Profit and Loss", 16, 5, 8, 3, category=CAT_ANALYTICS),
    ModuleSpec("pl_daily", "Profit And Loss - Daily", 16, 5, 8, 3, category=CAT_ANALYTICS),
    ModuleSpec("portfolio_vs_market", "Portfolio vs Market", 16, 5, 8, 3, category=CAT_ANALYTICS),
    ModuleSpec("coin_allocation", "Coin Allocation", 10, 6, 6, 3, category=CAT_OVERVIEW),
    ModuleSpec(
        "allocation_by_category", "Asset Allocation by Category", 12, 5, 6, 3, category=CAT_OVERVIEW
    ),
    ModuleSpec("asset_allocation", "Asset Allocation", 24, 3, 8, 2, category=CAT_OVERVIEW),
    ModuleSpec("heatmap", "Heatmap", 24, 8, 8, 8, category=CAT_ANALYTICS),
    ModuleSpec("top_gainers", "Top 5 Gainers", 12, 4, 6, 1, category=CAT_ANALYTICS),
    ModuleSpec("top_losers", "Top 5 Losers", 12, 4, 6, 1, category=CAT_ANALYTICS),
    ModuleSpec("inflows_outflows", "Inflows & Outflows", 24, 5, 8, 3, category=CAT_TRADING),
    ModuleSpec("trading_fees_paid", "Trading Fees Paid", 12, 3, 6, 3, category=CAT_TRADING),
    ModuleSpec("trading_fees_monthly", "Trading Fees - Monthly", 24, 5, 8, 3, category=CAT_TRADING),
    ModuleSpec("funding_fees", "Funding Fees Paid", 12, 3, 6, 2, category=CAT_TRADING),
    ModuleSpec("open_orders", "Open Orders", 12, 4, 6, 2, category=CAT_TRADING),
    ModuleSpec("open_positions", "Open Positions", 12, 4, 6, 2, category=CAT_TRADING),
    ModuleSpec("market_overview", "Market Overview", 12, 3, 6, 2, category=CAT_TRADING),
    ModuleSpec("fear_greed", "Fear & Greed", 8, 3, 4, 2, 8, 4, category=CAT_MORE),
    ModuleSpec("watchlist", "Watchlist", 12, 4, 6, 2, category=CAT_TRADING),
    ModuleSpec("recent_activity", "Recent Activity", 12, 4, 6, 2, category=CAT_TRADING),
    ModuleSpec("accounts_strip", "Accounts", 24, 2, 8, 2, 24, 3, category=CAT_OVERVIEW),
    ModuleSpec("drawdown", "Drawdown", 12, 4, 6, 2, category=CAT_ANALYTICS),
    ModuleSpec("risk_metrics", "Risk Metrics", 12, 3, 6, 2, category=CAT_ANALYTICS),
    ModuleSpec("best_worst_days", "Best & Worst Days", 12, 3, 6, 2, category=CAT_ANALYTICS),
    ModuleSpec("concentration", "Concentration", 8, 3, 4, 2, 12, 4, category=CAT_ANALYTICS),
    ModuleSpec("cash_drag", "Cash Drag", 8, 3, 4, 2, 12, 4, category=CAT_ANALYTICS),
    ModuleSpec("income_yield", "Income & Yield", 12, 3, 6, 2, category=CAT_ANALYTICS),
    ModuleSpec("trade_stats", "Trade Stats", 12, 3, 6, 2, category=CAT_TRADING),
    ModuleSpec("exposure_by_venue", "Exposure by Venue", 12, 4, 6, 2, category=CAT_TRADING),
    ModuleSpec("rebalance_drift", "Rebalance Drift", 12, 4, 6, 2, category=CAT_TRADING),
    ModuleSpec("goals_progress", "Goals", 12, 4, 6, 2, category=CAT_MORE),
    ModuleSpec("tax_lots_summary", "Tax Lots Summary", 12, 4, 6, 2, category=CAT_MORE),
    ModuleSpec("events_calendar", "Events Calendar", 24, 6, 8, 3, category=CAT_ANALYTICS),
    ModuleSpec("timeline", "Snapshot Timeline", 24, 3, 8, 2, category=CAT_ANALYTICS),
    ModuleSpec("advanced", "Tools", 24, 6, 8, 3, category=CAT_MORE),
)

MODULE_IDS: frozenset[str] = frozenset(m.id for m in CATALOG)
_BY_ID: dict[str, ModuleSpec] = {m.id: m for m in CATALOG}


def spec_for(module_id: str) -> ModuleSpec | None:
    return _BY_ID.get(module_id)


def title_for(module_id: str) -> str:
    spec = _BY_ID.get(module_id)
    return spec.title if spec else module_id


def effective_spec(
    module_id: str,
    module_mins: dict[str, tuple[int, int]] | None = None,
) -> ModuleSpec | None:
    """Catalog spec with optional user min_w/min_h overrides from layout prefs."""
    base = _BY_ID.get(module_id)
    if base is None:
        return None
    if not module_mins or module_id not in module_mins:
        return base
    min_w, min_h = module_mins[module_id]
    min_w = max(1, min(base.max_w, int(min_w)))
    min_h = max(1, min(base.max_h, int(min_h)))
    return replace(base, min_w=min_w, min_h=min_h)


def catalog_by_category() -> list[tuple[str, list[ModuleSpec]]]:
    """Ordered (category, specs) groups for Settings / Customize UI."""
    buckets: dict[str, list[ModuleSpec]] = {c: [] for c in CATEGORY_ORDER}
    for spec in CATALOG:
        key = spec.category if spec.category in buckets else CAT_MORE
        buckets[key].append(spec)
    return [(cat, buckets[cat]) for cat in CATEGORY_ORDER if buckets[cat]]


# Factory page placements (24-col square grid).
DEFAULT_PAGES: tuple[dict, ...] = (
    {
        "id": "overview",
        "name": S.PORTFOLIO_TAB_OVERVIEW,
        "placements": [
            {"id": "total_worth", "col": 0, "row": 0, "w": 16, "h": 5},
            {"id": "pl_insights", "col": 16, "row": 0, "w": 8, "h": 5},
            {"id": "assets", "col": 0, "row": 5, "w": 24, "h": 11},
            {"id": "portfolio_value", "col": 0, "row": 16, "w": 14, "h": 5},
            {"id": "coin_allocation", "col": 14, "row": 16, "w": 10, "h": 5},
        ],
    },
    {
        "id": "analytics",
        "name": S.PORTFOLIO_TAB_ANALYTICS,
        "placements": [
            {"id": "cumulative_pnl", "col": 0, "row": 0, "w": 12, "h": 5},
            {"id": "pl_daily", "col": 12, "row": 0, "w": 12, "h": 5},
            {"id": "portfolio_vs_market", "col": 0, "row": 5, "w": 24, "h": 5},
            {"id": "heatmap", "col": 0, "row": 10, "w": 12, "h": 8},
            {"id": "events_calendar", "col": 12, "row": 10, "w": 12, "h": 8},
            {"id": "asset_allocation", "col": 0, "row": 18, "w": 24, "h": 3},
            {"id": "top_gainers", "col": 0, "row": 21, "w": 12, "h": 4},
            {"id": "top_losers", "col": 12, "row": 21, "w": 12, "h": 4},
        ],
    },
    {
        "id": "trading",
        "name": "Trading",
        "placements": [
            {"id": "open_orders", "col": 0, "row": 0, "w": 12, "h": 4},
            {"id": "open_positions", "col": 12, "row": 0, "w": 12, "h": 4},
            {"id": "trading_fees_paid", "col": 0, "row": 4, "w": 12, "h": 3},
            {"id": "funding_fees", "col": 12, "row": 4, "w": 12, "h": 3},
            {"id": "trading_fees_monthly", "col": 0, "row": 7, "w": 24, "h": 5},
            {"id": "inflows_outflows", "col": 0, "row": 12, "w": 24, "h": 5},
        ],
    },
)

# Chip labels mapped onto PERFORMANCE_RANGES keys (plus ytd/all handled in UI).
RANGE_CHIPS: tuple[tuple[str, str], ...] = (
    ("24h", S.PORTFOLIO_CHIP_24H),
    ("7d", S.PORTFOLIO_CHIP_1W),
    ("1m", S.PORTFOLIO_CHIP_1M),
    ("3m", S.PORTFOLIO_CHIP_3M),
    ("6m", S.PORTFOLIO_CHIP_6M),
    ("1y", S.PORTFOLIO_CHIP_1Y),
    ("ytd", S.PORTFOLIO_CHIP_YTD),
    ("all", S.PORTFOLIO_CHIP_ALL),
)
