"""Dashboard module body factory."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import QWidget

from trendalgo.device.context import DeviceContext
from trendalgo.device.portfolio_model import PortfolioOverview
from trendalgo.device.views.modules.allocation_modules import (
    AssetAllocationModule,
    CategoryAllocationModule,
    CoinAllocationModule,
    HeatmapModule,
)
from trendalgo.device.views.modules.assets_module import AssetsModule
from trendalgo.device.views.modules.chart_modules import (
    CumulativePnlModule,
    DailyPnlModule,
    PortfolioValueModule,
    PortfolioVsMarketModule,
)
from trendalgo.device.views.modules.core_modules import PlInsightsModule, TotalWorthModule
from trendalgo.device.views.modules.events_calendar_module import EventsCalendarModule
from trendalgo.device.views.modules.extra_modules import ExtraModule
from trendalgo.device.views.modules.fee_flow_modules import (
    FundingFeesModule,
    InflowsOutflowsModule,
    TradingFeesMonthlyModule,
    TradingFeesPaidModule,
)
from trendalgo.device.views.modules.orders_modules import (
    OpenOrdersModule,
    OpenPositionsModule,
    TopGainersModule,
    TopLosersModule,
)
from trendalgo.device.views.modules.wrap_modules import AdvancedModule, TimelineModule

ModuleBody = QWidget


def build_module(
    module_id: str,
    ctx: DeviceContext,
    *,
    on_range: Callable[[str], None] | None = None,
    on_calendar_setup: Callable[[], None] | None = None,
) -> ModuleBody:
    builders: dict[str, Callable[[], ModuleBody]] = {
        "total_worth": lambda: TotalWorthModule(on_range=on_range),
        "pl_insights": PlInsightsModule,
        "assets": AssetsModule,
        "portfolio_value": lambda: PortfolioValueModule(on_range=on_range),
        "cumulative_pnl": lambda: CumulativePnlModule(on_range=on_range),
        "pl_daily": lambda: DailyPnlModule(on_range=on_range),
        "portfolio_vs_market": lambda: PortfolioVsMarketModule(on_range=on_range),
        "coin_allocation": CoinAllocationModule,
        "allocation_by_category": CategoryAllocationModule,
        "asset_allocation": AssetAllocationModule,
        "heatmap": HeatmapModule,
        "top_gainers": TopGainersModule,
        "top_losers": TopLosersModule,
        "inflows_outflows": lambda: InflowsOutflowsModule(on_range=on_range),
        "trading_fees_paid": TradingFeesPaidModule,
        "trading_fees_monthly": lambda: TradingFeesMonthlyModule(on_range=on_range),
        "funding_fees": FundingFeesModule,
        "open_orders": OpenOrdersModule,
        "open_positions": OpenPositionsModule,
        "events_calendar": lambda: EventsCalendarModule(ctx, on_setup=on_calendar_setup),
        "timeline": TimelineModule,
        "advanced": lambda: AdvancedModule(ctx),
    }
    factory = builders.get(module_id)
    if factory is not None:
        return factory()
    return ExtraModule(module_id)


def bind_overview(
    module: ModuleBody, overview: PortfolioOverview | None, *, range_key: str
) -> None:
    binder = getattr(module, "set_overview", None)
    if callable(binder):
        binder(overview, range_key=range_key)
